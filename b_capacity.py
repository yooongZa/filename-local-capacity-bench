"""B: 로컬 장비의 이미지 수·컨텍스트·동시 요청·반복 실행 한계를 측정합니다.

처음에는 python b_capacity.py --mock 으로 저장·검사 흐름을 확인하세요.
실제 모델·서버 경로와 실험값은 configs/b_local.json에서 바꿉니다.
"""
from filename_bench.runner import main

if __name__ == "__main__":
    main("b")
