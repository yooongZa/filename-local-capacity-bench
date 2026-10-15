# 검증 기록

- 프로젝트 명칭: filename
- 선택 모델 표시명: `google/gemma-4-12b-qat`
- 자동 테스트: 18개 통과
- Python 문법·설정 JSON·노트북 구조·diff 공백 검사: 통과
- 사용자 ZIP 가져오기: 정상·기존 폴더 보존·외부 경로 차단·손상 파일·취소·재시도 확인
- 사진만 또는 영상만 있는 입력: 모의 실행·리포트 통과
- 기존 입력 목록(`model_inputs.jsonl`)·응답 원문·재개·사람 평가 보존: 회귀 테스트 통과
- 실제 GPU 모델 다운로드·추론: 미실행

검증 명령:

```bash
python -m unittest discover -s tests -v
python upload_dataset.py evaluation.zip --destination data/evaluation
python b_capacity.py --dataset-root data/evaluation --dry-run
python b_capacity.py --dataset-root data/evaluation --mock --run-dir runs/check
```

압축에 바깥 폴더가 있으면 업로드 명령이 출력한 경로를 `--dataset-root`에 지정합니다. `tests/`의 작은 임시 이미지는 코드 검사용이고 실제 품질 평가에 사용하지 않습니다. 평가 데이터·정답을 생성하는 실행 경로는 없습니다.

CLI에서 ZIP 가져오기 → --dry-run → --mock → 리포트까지 기존 이미지 파일의 복사본으로 확인했습니다(2요청). HTTP 시험에는 가짜 서버를 사용했습니다. POSIX 전용 시험은 Windows에서 건너뜁니다.

실제 A100·Windows 8GB VRAM·Mac Metal에서 Gemma 4 Unified 12B QAT 모델을 로드하고, 지원 옵션·토큰 수·품질·메모리를 확인해야 합니다. A의 BF16 실행과 B의 Q4 GGUF 실행은 정밀도가 다릅니다. 모의 실행 결과는 모델 성능으로 해석하지 않습니다.

Based-On: none — 직접 대응하는 LMS 예제가 없어 작성한 project_extension입니다. LMS 원문은 포함하지 않습니다.
