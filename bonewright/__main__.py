"""`python3 -m bonewright …` = `bw …`. `bw` 가 PATH 에 없을 때(새 터미널에서 venv 를 안 켬·`pip install --user`·Windows Scripts)
흔히 치는 대안이 "No module named bonewright.__main__" 이었다(10/14 17회차 실측)."""
import sys

from .cli import main

sys.exit(main())
