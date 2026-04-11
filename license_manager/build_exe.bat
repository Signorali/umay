@echo off
echo Building Umay License Manager...
echo.

pip install cryptography customtkinter pyinstaller --quiet

pyinstaller ^
  --onefile ^
  --windowed ^
  --name "UmayLicenseManager" ^
  --add-data "%LOCALAPPDATA%\Python\pythoncore-3.14-64\Lib\site-packages\customtkinter;customtkinter" ^
  umay_license_manager.py

echo.
if exist dist\UmayLicenseManager.exe (
    echo SUCCESS: dist\UmayLicenseManager.exe hazir!
) else (
    echo HATA: Build basarisiz, yukarıdaki hatalara bakin.
)
pause
