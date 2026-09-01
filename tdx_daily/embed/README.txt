本目录需放置通达信 datatool 可执行文件，文件名为：

  datatool

（Linux 无扩展名；Windows 可为 datatool.exe，若你有官方名称请改名为 datatool 或自行修改
download_g4day_daily.py / update_minline_standalone.py 中的 --datatool 路径。）

来源：从本机已安装的通达信软件目录中拷贝官方提供的 datatool。
仓库通常不提交该二进制（体积/授权/平台差异）。

Windows：若不确定安装路径，可在 TDX_daily 目录执行
  python find_copy_datatool.py
  python find_copy_datatool.py --copy
（--copy 将找到的 datatool.exe 复制到本目录 embed/datatool.exe）
也可设置环境变量 TDX_DATATOOL=完整路径\datatool.exe，无需拷贝到 embed。

日线：``download_g4day_daily.py`` 默认用 **Python** ``tdx_native_day_merge``（与原 tdx2db 日线合并一致），一般**无需**
本目录下的 datatool；仅在 ``--use-external-datatool`` 时才需要此处可执行文件，且须支持子命令： day create ...
分时流程需要： tick create ... / min create ...

Linux x86_64 若运行 32 位 datatool，可能需要：sudo apt install libc6-i386

同目录下的 datatool.ini 可能被运行时在 work 目录下生成的配置覆盖，以脚本逻辑为准。
