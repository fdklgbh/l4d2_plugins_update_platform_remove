# -*- coding: utf-8 -*-
# @Time: 2024/10/27
# @Author: Administrator
# @File: plugins_remove_up_platform.py

import configparser
import os
from pathlib import Path
from logzero import setup_logger
import platform
import sys
import shutil


def is_win():
    return platform.system().lower() == 'windows'


def is_linux():
    return platform.system().lower() == 'linux'


def read(file: Path, folder=False, encoding='utf-8'):
    try:
        with open(file, 'r', encoding=encoding) as f:
            for line in f:
                if not folder:
                    if line.startswith('NEWFLDR'):
                        continue
                    res = line.strip().replace('\\', '/')
                    yield res
                else:
                    if line.startswith('NEWFLDR'):
                        yield line.strip().replace('\\', '/')
    except UnicodeError:
        logger.warning(f'读取日志文件出现编码错误:{file_to_plugins_name(file)},用gbk编码重试')
        yield from read(file, folder, 'gbk')


def file_to_plugins_name(file: Path) -> str:
    return file.stem.replace(' install', '')


def get_source_path(line: str):
    return Path(gamePath) / line


def remove():
    logger.info(f'插件日志文件夹:{installLogsPath}')
    logger.info(f'游戏目录:{gamePath}')
    if not installLogsPath.exists():
        raise FileNotFoundError(f'文件夹未找到:{installLogsPath}')

    for file in installLogsPath.glob('*install.log'):
        for line in read(file):
            source_file = get_source_path(line)
            if not source_file.exists():
                logger.error(f'读取插件:{file_to_plugins_name(file)}文件不存在: {source_file}')
            else:
                source_file.unlink()


def up_plugins():
    old = input("旧版插件平台文件夹:")
    new = input("新版插件平台文件夹:")
    if any(not i for i in [old, new]):
        logger.error('需要传入文件夹绝对路径')
        pause(True)
    old = Path(old)
    new = Path(new)
    for i in [old, new]:
        if not i.exists():
            logger.error('文件夹不存在')
            return
        elif not i.is_absolute():
            logger.error('文件夹不为绝对路径')
        try:
            i.relative_to(mod_folder)
        except ValueError:
            logger.error(f'插件平台{i.name}不在{mod_folder}目录下')
            return

    if any(not i.exists() or not i.is_absolute() or str(i.relative_to(mod_folder)).startswith('left4dead2') for i in
           [old, new]):
        logger.error(
            f'需要传入插件目录以及目录绝对路径,可以拖动文件夹到黑窗口中,或者路径不是在配置文件夹{mod_folder.name}')
    # 处理旧插件文件
    logger.info('处理旧插件平台日志文件以及启用文件')
    old_plugins_name = old.name
    old_log = installLogsPath / f'{old_plugins_name} install.log'
    new_plugins_name = new.name
    new_log = installLogsPath / f'{new_plugins_name} install.log'
    for line in read(old_log):
        source_file = get_source_path(line)
        if source_file.exists():
            source_file.unlink()
        else:
            logger.warning(f"{old_plugins_name}插件中文件不存在:{source_file}")
    logger.info('清理文件完毕，开始删除日志文件')
    old_log.unlink()
    logger.info('开始复制新插件文件信息')
    for data, is_folder in get_log_data(new):
        path = new / data
        target_path = gamePath / data
        if is_folder:
            target_path.mkdir(exist_ok=True)
        else:
            logger.debug(f'{path} ==> {target_path}')
            shutil.copy(path, gamePath / data)
    logger.info('复制文件结束，开始写入插件安装日志')
    with open(new_log, 'w', encoding='utf8') as f:
        f.write(platform_plugins_info)
    logger.info('插件安装日志写入完毕，开始替换ini文件内容')
    with open(installLogsPath.parent / 'JSGME.ini', 'r+', encoding='gbk') as f:
        data = f.read()
        data = data.replace(old_plugins_name, new_plugins_name)
        f.seek(0)
        f.truncate()
        f.flush()
        f.write(data)
    logger.info('替换完成')
    logger.info('程序退出...')


def get_log_data(new: Path):
    """
    生成日志内容
    :return:
    """
    global platform_plugins_info
    for data in directory_contents(new):
        is_folder = data.is_dir()
        data = data.relative_to(new)
        if str(data) in ['left4dead2', r'left4dead2\addons', '.']:
            continue
        info = data
        if is_folder:
            info = 'NEWFLDR|' + str(data) + '\\'
        platform_plugins_info += f'{info}\n'
        yield data, is_folder


def directory_contents(directory: Path, level=0):
    yield directory
    items = list(directory.glob('*'))
    for item in items:
        if item.is_file():
            yield item
    for item in items:
        if item.is_dir():
            yield from directory_contents(item, level + 1)


def main():
    print(f'当前平台是: {platform.system()}')
    print('Windows平台替换新旧插件平台')
    print('Linux平台根据jsgme生成的!INSTLOGS文件夹删除已安装的插件文件')
    if is_win():
        up_plugins()
    elif is_linux():
        remove()
        logger.info('删除插件安装日志文件夹')
        shutil.rmtree(installLogsPath)
        logger.info(f'{installLogsPath}文件夹删除完成')


def pause(exit_=True):
    if is_win():
        os.system('pause')
    if exit_:
        sys.exit()


if __name__ == '__main__':
    logger = setup_logger(__name__)
    need_pause = False
    try:
        platform_plugins_info = ''
        config = configparser.ConfigParser()
        config.read('env.ini')
        gamePath = config.get('plugins', 'gamePath')
        instLogs = config.get('plugins', 'installLogs')
        mod_folder = config.get('plugins', 'modFolder', fallback=None)
        if not gamePath or not instLogs:
            logger.error('gamePath和inStLogs参数必填')
            pause(True)
        if is_win() and not mod_folder:
            logger.error('Windows需要配置')
            pause(True)
        if is_win():
            mod_folder = Path(mod_folder).absolute()
        installLogsPath = Path(instLogs).absolute()
        gamePath = Path(gamePath).absolute()

        msg = '{}路径不存在,程序退出'
        if is_win() and not installLogsPath.exists():
            logger.error(msg.format('插件安装文件夹'))
            pause(True)
        if not gamePath.exists():
            logger.error(msg.format('游戏'))
            pause(True)
        main()
    except configparser.NoSectionError:
        logger.error(
            '需要在当前目录下创建env.ini,配置节点plugins,及其参数gamePath installLogs modFolder\ngamePath(left4dead2文件夹所在目录)\ninstallLogs(!INSTLOGS目录)\nmodFolder(插件目录,一般是JS-MODS)')
        pause()
    except Exception as e:
        logger.exception(f'发生未处理异常：\n{e}')
        pause()
