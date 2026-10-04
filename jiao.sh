cd ~/CEDA
rm -rf build
pyinstaller --onefile --windowed \
    --add-binary="/home/yxk/.virtualenvs/CEDA/lib/python3.10/site-packages:site-packages" \
    --add-data="/home/yxk/CEDA/device_generation:device_generation" \
    --add-data="/home/yxk/CEDA/analog_placement:analog_placement" \
    --add-data="/home/yxk/CEDA/ota_case1:ota_case1" \
    --add-data="/home/yxk/CEDA/rsmt_router:rsmt_router" \
    --add-data="/home/yxk/CEDA/assets:assets" \
    --hidden-import PyQt5.QtCore \
    --hidden-import PyQt5.QtGui \
    --hidden-import PyQt5.QtWidgets \
    --hidden-import PyQt5.sip \
    --name="parms" \
    main_ui.py

#pyinstaller --onefile --windowed \
#    --add-binary="/home/yxk/.virtualenvs/CEDA/lib/python3.10/site-packages/gdspy:gdspy" \
#    --add-binary="/home/yxk/.virtualenvs/CEDA/lib/python3.10/site-packages/gymnasium:gymnasium" \
#    --add-binary="/home/yxk/.virtualenvs/CEDA/lib/python3.10/site-packages/PyQt5:PyQt5" \
#    --add-binary="/home/yxk/.virtualenvs/CEDA/lib/python3.10/site-packages/PyQt5/Qt5:PyQt5/Qt5" \
#    --add-binary="/home/yxk/.virtualenvs/CEDA/lib/python3.10/site-packages/matplotlib:matplotlib" \
#    --add-binary="/home/yxk/.virtualenvs/CEDA/lib/python3.10/site-packages/mpl_toolkits:mpl_toolkits" \
#    --add-binary="/home/yxk/.virtualenvs/CEDA/lib/python3.10/site-packages/tabulate:tabulate" \
#    --add-binary="/home/yxk/.virtualenvs/CEDA/lib/python3.10/site-packages/torch_geometric:torch_geometric" \
#    --add-binary="/home/yxk/.virtualenvs/CEDA/lib/python3.10/site-packages/dgl:dgl" \
#    --add-binary="/home/yxk/.virtualenvs/CEDA/lib/python3.10/site-packages/IPython:IPython" \
#    --add-binary="/home/yxk/.virtualenvs/CEDA/lib/python3.10/site-packages/stack_data:stack_data" \
#    --add-binary="/home/yxk/.virtualenvs/CEDA/lib/python3.10/site-packages/pickleshare.py:."
#    --add-binary="/home/yxk/CEDA/rsmt_router/gdsii:rsmt_router/gdsii" \
#    --add-data="/home/yxk/CEDA/rsmt_router/UnionFind.py:." \
#    --add-data="/home/yxk/CEDA/device_generation:device_generation" \
#    --add-data="/home/yxk/CEDA/analog_placement:analog_placement" \
#    --add-data="/home/yxk/CEDA/ota_case1:ota_case1" \
#    --add-data="/home/yxk/CEDA/rsmt_router:rsm_router" \
#    --collect-all asttokens \
#    --collect-all backcall \
#    --collect-all certifi \
#    --collect-all click \
#    --collect-all cloudpickle \
#    --collect-all contourpy \
#    --collect-all cycler \
#    --collect-all executing \
#    --collect-all filelock \
#    --collect-all idna \
#    --collect-all jedi \
#    --collect-all joblib \
#    --collect-all kiwisolver \
#    --collect-all mpmath \
#    --collect-all networkx \
#    --collect-all numpy \
#    --collect-all packaging \
#    --collect-all pandas \
#    --collect-all parso \
#    --collect-all pexpect \
#    --collect-all prompt_toolkit \
#    --collect-all psutil \
#    --collect-all ptyprocess \
#    --collect-all pure_eval \
#    --collect-all pytz \
#    --collect-all requests \
#    --collect-all scipy \
#    --collect-all sympy \
#    --collect-all torch \
#    --collect-all tqdm \
#    --collect-all traitlets \
#    --collect-all tzdata \
#    --collect-all urllib3 \
#    --collect-all wcwidth \
#    --hidden-import PyQt5.QtCore \
#    --hidden-import PyQt5.QtGui \
#    --hidden-import PyQt5.QtWidgets \
#    --hidden-import PyQt5.sip \
#    --name="parms" \
#    main_ui.py