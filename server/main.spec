import sys
from PyInstaller.utils.hooks import collect_all, copy_metadata

sys.setrecursionlimit(sys.getrecursionlimit() * 5)

datas = []
binaries = []
hiddenimports = []

# --- 定义工具函数 ---
def safe_collect(package_name):
    global datas, binaries, hiddenimports
    try:
        tmp_ret = collect_all(package_name)
        datas += tmp_ret[0]
        binaries += tmp_ret[1]
        hiddenimports += tmp_ret[2]
        try:
            datas += copy_metadata(package_name)
        except Exception:
            pass 
    except Exception as e:
        print(f"WARNING: Could not collect {package_name}: {e}")

def safe_copy_metadata(package_name):
    try:
        return copy_metadata(package_name)
    except Exception as e:
        print(f"WARNING: No metadata for {package_name}: {e}")
        return []

# --- 2. 收集常规依赖 ---
safe_collect('trafilatura')
safe_collect('justext') 
safe_collect('spacy_transformers')
safe_collect('spacy_alignments')
safe_collect('spacy_curated_transformers')
safe_collect('spacy_curated_transformers.pipeline')
safe_collect('curated_transformers')


datas += safe_copy_metadata('spacy_transformers')
datas += safe_copy_metadata('spacy_curated_transformers')
datas += safe_copy_metadata('curated_transformers')


# --- 4. Hidden Imports ---
hiddenimports += [
    'spacy_transformers',
    'spacy_transformers.architectures',
    'spacy_transformers.pipeline_component',
    
    # Curated Transformers 组件
    'spacy_curated_transformers',
    'spacy_curated_transformers.architectures',
    'spacy_curated_transformers.pipeline',
    'curated_transformers',
]

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='DeepReader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='DeepReader',
)