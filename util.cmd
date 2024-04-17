pyuic5 mainWin.ui -o mainWin_ui.py

@REM 打包命令
pyinstaller -D ./main.py -i ./rc/main.ico -n "SCPI GUI" --distpath=.

@REM 无控制台打包
pyinstaller -D ./main.py -i ./rc/main.ico -n "SCPI GUI" --distpath=. -w

@REM 新建环境

conda update -n base -c defaults conda

conda create -n scd

conda activate scd

conda install python

pip install pyqt5 pyinstaller pyqt5-tools pyqt5-stubs
