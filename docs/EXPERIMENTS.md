# 실험 실행 방법


Gemma 4 멀티모달을 지원하는 `llama-server` 실행 파일과 **서로 호환되는 GGUF 모델·mmproj**를 준비합니다. 설치·다운로드는 이 스크립트가 자동으로 수행하지 않습니다.

`configs/b_local.json`에서 아래 값을 실제 파일에 맞게 입력하세요.

```json
{
  "server_path": "C:/llama/llama-server.exe",
  "model_path": "C:/models/실제모델.gguf",
  "mmproj_path": "C:/models/실제프로젝터.gguf",
  "quantization_label": "실제 양자화 방식"
}
```

Mac에서는 위 경로를 Mac용 실행 파일·모델 경로로 바꿉니다. Metal 실행의 메모리 수치는 NVIDIA 전용 VRAM과 직접 비교할 수 없습니다. NVIDIA가 없는 환경에서는 GPU 메모리를 `null`로 기록합니다.

```bash
python b_capacity.py --dry-run
python b_capacity.py --suite smoke
python b_capacity.py --suite context
python b_capacity.py --suite images
python b_capacity.py --suite concurrency
python b_capacity.py --suite soak
```

| suite | 측정 내용 | 확인할 결과 |
|---|---|---|
| `smoke` | 사진 1장, 영상 3프레임 | 로드·이미지 입력·JSON 응답 |
| `context` | 요청당 4K/8K/16K/32K | 실제 토큰 점유율, 성공 여부, 메모리 |
| `images` | 같은 영상 1/3/6/12장 | 실제 이미지 수, 입력 토큰, 지연·오류 |
| `concurrency` | 독립 요청 1/2/4/8개 | 동시 실행 슬롯 관측치, 요청·그룹 시간 |
| `soak` | 모델을 유지하고 100회 요청 | 오류·시간·메모리 변화, 장면 간 답변 오염 |

**`concurrency`는 동시에 보내는 독립 요청 수입니다.** 하나의 요청에 넣는 이미지 수와 구분합니다. llama.cpp의 `-b`, `-ub`는 토큰 처리량 설정이며 사진 개수가 아닙니다. 이 예제는 진짜 Tensor batch(텐서 배치) 크기 탐색을 구현하지 않습니다.

B는 각 조건마다 서버를 새로 띄웁니다. 자동 메모리 맞춤을 끄고 GPU layers(레이어)를 명시하며, `/slots`에서 실제 요청당 컨텍스트와 슬롯 수가 요청값과 같은지 확인합니다. `--help`에 필요한 옵션이 없는 빌드는 `unsupported`로 중단합니다.

컨텍스트 실험은 먼저 기본 입력의 토큰 수를 측정하고, 서버의 `/tokenize`로 중립 텍스트를 추가해 입력이 컨텍스트의 약 75%를 사용하도록 구성합니다. 성공 응답의 실제 토큰 사용량이 목표에 근접했는지 `context_load_confirmed`로 확인합니다. **75% 입력 부하의 실행 확인이며 컨텍스트를 끝까지 채운 한계값을 증명하지 않습니다.** 출력 여유도 남깁니다. 이 인공 입력은 의미 품질 평가에서 제외합니다.

동시성은 클라이언트 요청 수, 서버 슬롯 수, `observed_active_slots_peak`를 함께 봅니다. 표본 측정 간격 사이에 끝난 짧은 요청은 관측에서 빠질 수 있습니다. 요청을 8개 보냈다는 사실만으로 GPU에서 8개가 동시에 실행됐다고 결론 내리지 않습니다.

전체 장치 메모리는 `nvidia-smi`로 약 0.5초 간격 측정하고, 서버 프로세스 RAM은 `psutil`로 측정합니다. 동시 요청의 VRAM은 그룹 전체 값입니다. 다른 GPU 프로그램도 수치에 영향을 주며 순간 최대치·모델 로딩 중 최대치는 놓칠 수 있습니다. A의 PyTorch 최대 할당·예약 메모리는 별도 필드입니다. GPU offload(오프로딩)가 실제로 완료됐는지는 저장된 서버 로그에서 확인해야 합니다.

`request_wall_s`는 요청 완료까지의 시간입니다. 첫 토큰 시간(TTFT)은 이 예제에서 측정하지 않습니다. GPU 종류·드라이버와 실제 장비 RAM은 별도로 실험 기록에 함께 적으세요. 여러 GPU가 있다면 `gpu_index`의 장치 전체 메모리만 수집합니다.

메모리 부족·시간 초과·서버 오류가 발생하면 현재 실행을 멈추고 소유한 서버를 종료합니다. 조건별 로그와 확보한 결과로 리포트를 생성합니다. 성공한 최대 조건은 **시험한 범위의 최대값**입니다. 최종 운영값은 여유 메모리와 반복 실행으로 다시 결정하세요.
