# AGENTS.md — ws_livox 工作区指南

本文件汇总本工作区的结构、环境、构建/运行方式与重要本地修改,供在此工作的 AI 编码代理快速上手。

## 1. 工作区概览

- **用途**: Livox 固态激光雷达 + FAST-LIO2 的 LiDAR(-IMU) SLAM 演示工作区。
  运行链路: `livox_ros2_driver` 发布 Livox 自定义点云消息 → `fast_lio`(FAST-LIO2 ROS2 移植版)建图,
  可视化通过 Lichtblick + foxglove_bridge 完成。
- **ROS 发行版**: Humble(Ubuntu 22.04, Python 3.10),系统安装于 `/opt/ros/humble`。
  另存在 miniforge conda 环境 `/home/dai/miniforge3/envs/ros_env`(仅被 Lichtblick layout 服务器脚本使用)。
- **默认激光雷达**: Livox Avia(`config/avia.yaml` 为默认配置)。

## 2. 目录结构

```
ws_livox/
├── src/                      # ROS 包源码(同时是一个 git 仓库,见 §6)
│   ├── FAST_LIO_ROS2/        # FAST-LIO2 的 ROS2 移植(fork 自 Ericsii/FAST_LIO_ROS2,含大量本地修改)
│   ├── livox_ros2_driver/    # Livox ROS2 驱动(上游 Livox-SDK 仓库,未修改)
│   ├── livox_interfaces/     # Livox 自定义消息(CustomMsg / CustomPoint)
│   ├── livox_sdk_vendor/     # 自动构建 Livox-SDK 的 vendor 包
│   ├── README.md / README_CN.md   # livox_ros2_driver 上游说明
│   └── images/               # README 配图
├── build/                    # colcon 构建目录(4 个包: fast_lio, livox_interfaces, livox_ros2_driver, livox_sdk_vendor)
├── install/                  # colcon 安装目录(构建产物,含 fast_lio 可执行文件 fastlio_mapping)
├── log/                      # 构建日志;latest → latest_build → 最近一次构建目录的符号链接链
├── livox_fast.zip            # src/ 的 362MB 快照备份(2026-08-21)
└── .vscode/                  # VS Code 配置(ROS2.distro = humble)
```

## 3. 各包职责

| 包 | 作用 | 关键内容 |
|---|---|---|
| `livox_sdk_vendor` | 以 CMake 自动拉取并编译 Livox-SDK,无需手动安装 SDK | — |
| `livox_interfaces` | 定义 `CustomMsg` / `CustomPoint` 自定义消息 | `msg/` |
| `livox_ros2_driver` | 连接 Livox 设备,发布 `/livox/lidar`(CustomMsg 或 PointCloud2)与 `/livox/imu` | `launch/`、`config/*.json` |
| `fast_lio` | FAST-LIO2 建图:订阅 `/livox/lidar`(CustomMsg)+ `/livox/imu`,发布 `/cloud_registered`、`/path` 等 | `src/laserMapping.cpp`、`config/*.yaml`、`launch/mapping.launch.py` |

**依赖关系**: `fast_lio` 依赖 `livox_interfaces`(注意:**不**依赖 `livox_ros_driver2`,这是本地改动的重点,见 §5)。

## 4. 构建

```bash
# bash 用户
source /opt/ros/humble/setup.bash
cd /home/dai/code/ws_livox
colcon build --symlink-install   # 已使用 symlink-install(build/fast_lio/ament_cmake_symlink_install 存在)
source ./install/setup.bash
```

```zsh
# zsh 用户(本机默认 shell 为 zsh,~/.zshrc 已 source /opt/ros/humble/setup.zsh)
source /opt/ros/humble/setup.zsh
cd /home/dai/code/ws_livox
colcon build --symlink-install
source ./install/setup.zsh       # 必须用 setup.zsh,不能沿用 setup.bash
```

- **zsh 下绝不能 source `setup.bash`**:colcon 生成的 bash 脚本用 `${BASH_SOURCE[0]}` 定位自身目录,该变量在 zsh 中为空 →
  前缀被解析成**当前工作目录**(工作区根)而非 `install/`,于是报
  `no such file or directory: <ws>/local_setup.sh` 与 `not found: "<ws>/local_setup.bash"`;
  结果是 `/opt/ros/humble` 挂上了但 4 个工作区包没挂上(`ros2 pkg prefix fast_lio` → `Package not found`),
  还会在工作区根残留 `AMENT_CURRENT_PREFIX`。修复:改用 `setup.zsh`,或换 bash。

- 构建日志落在 `log/build_<日期时间>/`,`log/latest_build` 符号链接指向最近一次(如 `build_2026-10-15_17-55-34`)。
- 已知无害警告:`CMake Warning (dev) ... Policy CMP0074 is not set`(环境里 `PCL_ROOT=/usr` 被 CMake 忽略,消除方式:`unset PCL_ROOT` 或在 CMakeLists 中 `cmake_policy(SET CMP0074 NEW)`)、PCL 1.12 头文件触发的 boost/bind 弃用 `#pragma message`。
- 修改 `fast_lio` 源码后重新构建只需 `colcon build --symlink-install --packages-select fast_lio`。

## 5. 运行

### 5.1 启动驱动(必须先于 fast_lio)
```bash
ros2 launch livox_ros2_driver livox_lidar_msg_launch.py
```
- 必须用 `*_msg_launch.py` 版本,才会发布 `fast_lio` 订阅的 `CustomMsg` 自定义消息。
- 设备在 `src/livox_ros2_driver/config/livox_lidar_config.json` 中配置(broadcast_code);
  当前以白名单模式运行:仅 `3JEDK1700178121`(Livox Avia,设备 IP 192.168.1.112/24,主机 enp5s0 侧 192.168.1.50/24)
  为 `enable_connect: true`,另两条旧记录为 `false`(不进白名单)。只要有一条为 `true`,驱动即打印
  `Disable auto connect mode!` 并只连白名单内设备——这是为避免多雷达共用 `/livox/lidar`(`multi_topic = 0`)串味。
- 设备侧参数无需改动:Echo/Single First、Cartesian、IMU 200Hz、No Repetitive 与本工作区配置一致;雷达无 PPS/PTP 时保持
  `time_sync_en: false` 与 `enable_timesync: false` 即可。该 JSON 在 install 下是符号链接,**改配置无需 colcon build**。

### 5.2 启动建图
```bash
ros2 launch fast_lio mapping.launch.py
```
- 关键 launch 参数:`config_file`(默认 `avia.yaml`,可选 `horizon/mid360/ouster64/velodyne.yaml`)、
  `config_path`、`use_sim_time`(默认 false)、`lichtblick`(默认 true)。
- 启动时同时拉起:fastlio_mapping 节点、foxglove_bridge(端口 **8765**)、
  Lichtblick layout 服务器(端口 **8766**)和 Lichtblick 桌面应用(深链自动导入布局)。
- **主题与 launch 无关**:Lichtblick 1.28 的外观是应用级设置,存在 app 设置项 `colorScheme`
  (`dark`/`light`/未设置=`system`),主进程据此设 `nativeTheme.themeSource`;未设置时跟随系统主题。
  改法:app 内 **用户菜单 → Settings → General → Color scheme → Dark**,或让系统用深色
  (`gsettings set org.gnome.desktop.interface color-scheme prefer-dark`)。该版本**没有** `--color-scheme`
  之类的命令行开关,别指望在 `mapping.launch.py` 里加参数改主题。
- **Lichtblick 1.28.0 只有英文界面**:语言下拉是硬编码 `[{key:"en",value:"English"}]`,`i18n.init({resources:{en}})`
  静态打包(无运行时加载后端),上游 develop 分支的 `packages/suite-base/src/i18n/` 也只有 `en/`(24 个 namespace、
  约 29KB)。想汉化必须自己 fork 源码加 `zh/` 并重新构建 deb,改配置目录塞 JSON 无效。

## 6. Git 仓库结构(重要,勿混淆)

本工作区有**两层嵌套 git 仓库**,提交/查看改动时务必区分:

1. `src/` 自身是仓库 **Livox-SDK/livox_ros2_driver**(HEAD `1565b97`),
   其中 `FAST_LIO_ROS2/` 与 `.vscode/` 是**未跟踪**文件——在 `src/` 下 `git add` 不会包含它们。
2. `src/FAST_LIO_ROS2/` 是独立仓库 **Ericsii/FAST_LIO_ROS2**(HEAD `2fffc57`),
   承载了**全部未提交的本地修改**(`git status` 显示 9 个修改文件 + `lichtblick/` 未跟踪)。
3. `livox_ros2_driver/`、`livox_interfaces/`、`livox_sdk_vendor/` 均与上游一致,无本地改动。

## 7. FAST_LIO_ROS2 本地未提交修改(核心定制)

这些是理解本工作区行为的关键,重新 clone 上游会丢失:

- **消息依赖替换**: `livox_ros_driver2` → `livox_interfaces`(`CMakeLists.txt`、`package.xml`、
  `src/laserMapping.cpp` 中的 include 与订阅类型、`src/preprocess.cpp/.h`)。
- **建图参数调整**(`config/avia.yaml`): `point_filter_num` 3→2、`cube_side_length` 1000→200、
  `blind` 4.0→2.0;发布项改为 `path_en: true`、`dense_publish_en: true`(发原始去畸变点云)、
  `scan_bodyframe_pub_en: false`、`map_en: false`;`pcd_save.pcd_save_en: false`(要落盘 PCD 时再开)。
- **全局地图常驻累计**(`src/laserMapping.cpp`):
  - 新增 `pcl_global_map` 全局点云累加器,每帧体素滤波(`downSizeFilterPCD`,
    参数 `pcd_save.filter_size_pcd`,默认 0.3m),不再丢弃旧点 —— **只在 `pcd_save_en: true` 时运行**,
    且每次对整张图做 O(N) 滤波,地图越大越慢;
  - `publish_map`/`save_to_pcd`/退出保存均改为输出该全局地图;
  - 新增参数 `mapping.disable_fov_seg`(**avia.yaml 中现为 `false`**):设 `true` 会跳过 ikd-Tree 的
    FOV 裁剪使地图无界增长,静止长时间运行会卡死在 IEKF/ikd-Tree 最近邻 —— 已实测:进程存活、
    topic 上有 publisher,但 `/Odometry`、`/path`、`/cloud_registered` 零输出。
    要"全局地图不被裁剪"应依赖 `pcl_global_map`,不要关 FOV 裁剪。
- **可视化替换**: `launch/mapping.launch.py` 移除 RViz,改为启动 foxglove_bridge +
  `lichtblick/layout_server.py`(标准库实现的带 CORS 的静态服务器)+ Lichtblick 深链;
  新增 `lichtblick/` 目录(布局 JSON 与服务器脚本)并安装到 share。
- **Humble API 修复**: 服务回调签名改为 `std::shared_ptr<...::Request>`(`map_save_callback`)。
- 默认 `config_file` 由 `mid360.yaml` 改为 `avia.yaml`。

### 7.1 硬编码路径(注意)
`mapping.launch.py` 中写死了:
- Lichtblick 可执行文件: `/usr/bin/lichtblick`
- layout 服务器解释器: `/home/dai/miniforge3/envs/ros_env/bin/python`
- 端口: foxglove_bridge 8765、layout 服务器 8766
迁移到其他机器时需要同步修改。

## 8. 数据与日志输出

- **点云保存**: `pcd_save.pcd_save_en: true` 时,全局体素滤波地图在节点退出时写入
  `src/FAST_LIO_ROS2/PCD/scans.pcd`(二进制 PCD);`interval` 语义同上游。
- **运行日志**: `src/FAST_LIO_ROS2/Log/`(调试记录 `mat_pre.txt` 等,可用 `Log/plot.py` 绘制)。
- **构建日志**: `log/latest_build/`。

## 9. 注意事项

- 编译 `livox_ros2_driver` 前若 `/usr/local/lib/livox_sdk_static.a` 存在需删除/改名
  (本工作区用 vendor 包自建共享库,一般不受影响)。
- 驱动仅在直连 LiDAR 模式下支持 GPS 时间同步(`timesync_config` 见 `livox_lidar_config.json`)。
- `fast_lio` 包名与目录名不一致(包名 `fast_lio`,目录 `FAST_LIO_ROS2`),launch/install 一律用 `fast_lio`。
- `log/latest*` 是指向具体构建目录的符号链接,清理日志时勿破坏链接。
