# filename · B — 로컬 실행 용량 실험

llama-server로 이미지 수·컨텍스트 점유율·동시 요청·모델 재사용 한계를 측정합니다.

## 빠른 시작

Python 3.10 이상을 사용합니다.

```bash
git clone https://github.com/yooongZa/filename-local-capacity-bench.git
cd filename-local-capacity-bench
python -m venv .venv
# macOS/Linux: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

자동 테스트는 작은 합성 이미지를 임시 생성하므로 모델·평가 데이터가 없어도 실행할 수 있습니다.

평가 데이터 폴더를 `data/filename_eval24_1080/`에 준비한 뒤 실행합니다. 다른 위치를 쓰려면 `configs/b_local.json`의 `dataset_root`를 변경하세요. 상세 형식은 [데이터 준비](docs/DATASET.md)에 있습니다.

```bash
python b_capacity.py --dry-run
python b_capacity.py --mock --resume
```

모의 실행은 저장·검사·리포트 경로를 확인하는 고정 응답을 사용합니다. 모의 결과로 모델 품질·GPU 성능을 판단하지 않습니다.

실제 실행 전 `configs/b_local.json`의 `server_path`, `model_path`, `mmproj_path`, `quantization_label`을 입력합니다. `--mock`을 빼면 자체 llama-server 프로세스를 실행합니다. B의 배치는 concurrency(독립 요청 동시성) 기준입니다.

## 구성과 결과

- [b_capacity.py](b_capacity.py): 실행 진입점
- [configs/b_local.json](configs/b_local.json): 실험 설정
- [실험 실행 방법](docs/EXPERIMENTS.md): 조건별 실행과 해석
- [평가 방법](docs/EVALUATION.md): 자동 지표와 사람 평가표
- [재개·오류 처리](docs/RELIABILITY.md): 실패·중단·재시도 검증 범위
- [검증 기록](VALIDATION.md): 이 저장소에서 확인한 범위

결과는 `runs/b/<suite>/`에 저장됩니다. JSONL 원문, CSV 지표·사람 평가표, HTML 리포트를 생성합니다. 공통 `filename_bench` 코드는 각 저장소에 포함되어 있어 다른 저장소 설치가 필요하지 않습니다. 모델·미디어·실행 결과·로컬 설정은 Git에서 제외합니다.

## 관련 저장소와 범위

짝 프로젝트: [yooongZa/filename-model-quality-bench](https://github.com/yooongZa/filename-model-quality-bench)

실제 A100·Windows 8GB VRAM·Mac Metal 추론은 아직 검증하지 않았습니다. 참조 답안은 독립적인 사람 검수가 필요합니다.

**Based-On: none** — 대응하는 멀티모달 용량·품질 벤치마크 LMS 예제가 없어 별도로 작성한 `project_extension`입니다. LMS 원문은 포함하지 않습니다.

## 공식 참고 자료

- [Gemma 4 E4B](https://huggingface.co/google/gemma-4-E4B-it)
- [Transformers Gemma 4](https://huggingface.co/docs/transformers/model_doc/gemma4)
- [llama-server](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)
