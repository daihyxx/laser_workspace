import os.path

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, TimerAction
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch.conditions import IfCondition

from launch_ros.actions import Node


def generate_launch_description():
    package_path = get_package_share_directory('fast_lio')
    default_config_path = os.path.join(package_path, 'config')
    lichtblick_config_path = os.path.join(package_path, 'lichtblick')

    use_sim_time = LaunchConfiguration('use_sim_time')
    config_path = LaunchConfiguration('config_path')
    config_file = LaunchConfiguration('config_file')
    lichtblick_use = LaunchConfiguration('lichtblick')

    declare_use_sim_time_cmd = DeclareLaunchArgument(
        'use_sim_time', default_value='false',
        description='Use simulation (Gazebo) clock if true'
    )
    declare_config_path_cmd = DeclareLaunchArgument(
        'config_path', default_value=default_config_path,
        description='Yaml config file path'
    )
    declare_config_file_cmd = DeclareLaunchArgument(
        'config_file', default_value='avia.yaml',
        description='Config file'
    )
    declare_lichtblick_cmd = DeclareLaunchArgument(
        'lichtblick', default_value='true',
        description='Launch Lichtblick and Foxglove Bridge to monitor results'
    )

    fast_lio_node = Node(
        package='fast_lio',
        executable='fastlio_mapping',
        parameters=[PathJoinSubstitution([config_path, config_file]),
                    {'use_sim_time': use_sim_time}],
        output='screen'
    )

    # Foxglove Bridge websocket server (default port 8765) for Lichtblick
    foxglove_bridge_node = Node(
        package='foxglove_bridge',
        executable='foxglove_bridge',
        name='foxglove_bridge',
        condition=IfCondition(lichtblick_use)
    )

    # Serve the Lichtblick layout JSON over HTTP so Lichtblick can import it
    # automatically (layoutUrl only accepts http/https).
    layout_server_process = ExecuteProcess(
        cmd=['/home/dai/miniforge3/envs/ros_env/bin/python',
             os.path.join(lichtblick_config_path, 'layout_server.py'),
             '--directory', lichtblick_config_path,
             '--port', '8766'],
        condition=IfCondition(lichtblick_use)
    )

    # Deep link: auto-connect to the Foxglove Bridge websocket and import the
    # preconfigured layout (3D panel with /cloud_registered point cloud).
    # Note: data source params must use the "ds." prefix (e.g. ds.url).
    lichtblick_process = ExecuteProcess(
        cmd=['/usr/bin/lichtblick',
             'lichtblick://open?ds=foxglove-websocket'
             '&ds.url=ws://localhost:8765'
             '&layoutUrl=http://localhost:8766/fastlio_lichtblick.json'],
        condition=IfCondition(lichtblick_use)
    )

    ld = LaunchDescription()
    ld.add_action(declare_use_sim_time_cmd)
    ld.add_action(declare_config_path_cmd)
    ld.add_action(declare_config_file_cmd)
    ld.add_action(declare_lichtblick_cmd)

    ld.add_action(fast_lio_node)
    ld.add_action(foxglove_bridge_node)
    ld.add_action(layout_server_process)
    # Give foxglove_bridge and the layout server time to start up first
    ld.add_action(TimerAction(period=3.0, actions=[lichtblick_process]))

    return ld
