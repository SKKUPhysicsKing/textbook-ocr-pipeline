# Textbook OCR Pipeline

사진으로 촬영한 교재 페이지, 스캔 이미지 또는 PDF를 로컬에서 OCR하여 TXT와 JSON으로 저장하는 Python 프로토타입입니다. 기본 언어는 한국어와 영어(`kor+eng`)이며 원본 파일은 외부 서버로 전송되지 않습니다.

## 주요 기능

- JPG, PNG, TIFF, WebP 등 이미지 입력
- 단일 PDF 또는 이미지/PDF가 섞인 폴더 일괄 처리
- EXIF 회전 보정, 축소, 노이즈 제거, 자동 대비, Otsu 이진화, 기울기 보정
- Tesseract OCR을 이용한 한국어·영어 인식
- 페이지별 TXT/JSON, 전체 합본 TXT, 실행 manifest 출력
- 단어별 위치와 신뢰도 저장
- 전처리된 페이지 이미지 선택 저장

## 설치

Python 3.10 이상과 Tesseract 5가 필요합니다. Windows에서는 Tesseract 설치 프로그램에서 Korean language data를 선택하고 `tesseract.exe` 폴더를 `PATH`에 추가합니다.

```powershell
git clone https://github.com/SKKUPhysicsKing/textbook-ocr-pipeline.git
cd textbook-ocr-pipeline
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .
tesseract --list-langs
```

`--list-langs` 결과에 `eng`와 `kor`가 모두 있어야 합니다. Ubuntu에서는 다음을 사용합니다.

```bash
sudo apt update
sudo apt install tesseract-ocr tesseract-ocr-eng tesseract-ocr-kor
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

## 사용법

```bash
textbook-ocr "input/page.jpg" -o output --save-processed
textbook-ocr "input/textbook.pdf" -o output --pdf-dpi 300
textbook-ocr "input/pages" -o output
textbook-ocr "input/pages" -o output --lang eng --psm 3
textbook-ocr --help
```

## 출력 구조

```text
output/
├── combined.txt
├── manifest.json
├── pages/
│   ├── page_0001.txt
│   ├── page_0001.json
│   └── ...
└── processed/             # --save-processed 사용 시 생성
    ├── page_0001.png
    └── ...
```

`manifest.json`에는 입력 경로, OCR 설정, 페이지 수, 페이지별 평균 신뢰도가 기록됩니다. 페이지별 JSON에는 단어 텍스트, 신뢰도와 좌표가 포함됩니다.

## 촬영 권장 조건

- 페이지와 카메라가 최대한 평행하도록 촬영합니다.
- 그림자가 글자 위를 지나가지 않도록 균일하게 조명합니다.
- 페이지 전체가 프레임 안에 들어오게 하고 글자가 흐려지지 않도록 초점을 고정합니다.
- 수식, 표, 다단 편집은 일반 문장보다 오류가 많으므로 결과를 검수해야 합니다.

## 테스트

```bash
python -m unittest discover -s tests -v
```

## 현재 한계

- 수식의 LaTeX 변환과 표 구조 복원은 아직 지원하지 않습니다.
- 곡면 페이지의 원근·왜곡 보정은 후속 기능입니다.
- Tesseract 언어 데이터 품질에 따라 한영 혼합 문서 정확도가 달라집니다.
