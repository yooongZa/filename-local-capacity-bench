# 검증 기록

- 프로젝트 명칭: filename
- 자동 테스트: 11개 통과
- Python·설정 JSON·공개 업로드 파일 구조: 통과
- 실제 평가 입력을 사용한 모의 실행: 2요청 통과
- 코드·문서·설정에 이전 프로젝트 명칭이 남지 않았는지 확인
- 실제 GPU 추론: 미실행

검증 명령:

```bash
python -m unittest discover -s tests -v
python b_capacity.py --config configs/b_local.local.json --mock
```

로컬 검증에서는 Git에서 제외되는 설정 파일로 평가 데이터 위치를 지정했습니다. 결과·절대 데이터 경로·미디어·모델은 커밋하지 않습니다.

HTTP 서버 시험에는 모델을 사용하지 않는 테스트 서버를 사용했습니다. POSIX 전용 시험은 Windows에서 건너뜁니다. 실제 Windows 8GB VRAM·Mac Metal 실행은 별도 검증이 필요합니다.

Based-On: none — 직접 대응하는 LMS 예제가 없어 작성한 project_extension입니다. LMS 원문은 포함하지 않습니다.
