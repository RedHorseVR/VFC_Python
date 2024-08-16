
black %1
rem ause

echo -------------------------------
perl  TabsPythonParser.pl %1 
perl  TabsPythonParser.pl %1  > %1.vfc
echo -------------------------------
perl  C:\Users\luisr\OneDrive\Desktop\VFC_WORK\VFC_Python\black_pyparser\TabsPythonParser.pl %1 > %1.vfc
echo -------------------------------
perl  E:/Users/luisr/OneDrive/Desktop/VFC_WORK/VFC_Python/black_pyparser/TabsPythonParser.pl %1 > %1.vfc


pause