# Textbook OCR Pipeline

사진으로 촬영한 교재 페이지, 스캔 이미지 또는 PDF를 로컬에서 OCR하여 TXT와 JSON으로 저장하는 Python 프로토타입입니다. 영문 물리학 교재의 오인식을 줄이기 위해 기본 언어는 영어(`eng`)이며, 원본 파일은 외부 서버로 전송되지 않습니다.

## 주요 기능

- JPG, PNG, TIFF, WebP 등 이미지 입력
- 단일 PDF 또는 이미지/PDF가 섞인 폴더 일괄 처리
- 원본 보존형 OCR을 기본으로 하고 그레이스케일·이진화 전처리를 선택 지원
- 2단 교재의 중앙 여백 자동 검출과 열별 읽기 순서 복원
- 저해상도·낮은 신뢰도·예상하지 않은 문자에 대한 품질 경고
- EXIF 회전 보정, 선택적 확대/축소, 노이즈 제거, 자동 대비, Otsu 이진화, 기울기 보정
- Tesseract OCR을 이용한 한국어·영어 인식
- 페이지별 TXT/JSON, 전체 합본 TXT, 실행 manifest 출력
- 단어별 위치와 신뢰도 저장
- 전처리된 페이지 이미지 선택 저장

## 설치

Python 3.10 이상과 Tesseract 5가 필요합니다. Windows에서는 Tesseract 설치 프로그램에서 Korean language data를 선택하고 `tesseract.exe` 폴더를 `PATH`에 추가합니다.

Windows에서 폴더 생성부터 가상환경, Tesseract 한글 데이터, 첫 OCR 실행까지 따라 하려면 [Windows 상세 설치 가이드](docs/windows-setup.md)를 확인하세요.

```powershell
git clone https://github.com/SKKUPhysicsKing/textbook-ocr-pipeline.git
cd textbook-ocr-pipeline
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .
tesseract --list-langs
```

영문 교재에는 `eng`만 필요합니다. 한영 혼합 문서에 `--lang kor+eng`를 사용하려면 `--list-langs` 결과에 `eng`와 `kor`가 모두 있어야 합니다. Ubuntu에서는 다음을 사용합니다.

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
textbook-ocr "input/pages" -o output --lang kor+eng
textbook-ocr "input/pages" -o output --layout columns --column-psm 6
textbook-ocr "input/pages" -o output --preprocess grayscale --deskew
textbook-ocr "input/pages" -o output --preprocess binary --threshold 170
textbook-ocr "input/pages" -o output --upscale-width 1600
textbook-ocr --help
```

기본 설정은 이번 저장소에서 시험한 영문 2단 교재 사진에 맞춘 `--lang eng --preprocess raw --layout auto`입니다. 원본 이미지가 1600 px보다 좁으면 경고하지만, 정보가 손실된 압축 이미지를 무조건 확대하지는 않습니다. 확대가 도움이 되는지 비교하려면 `--upscale-width 1600`을 별도로 지정하세요.

## Google Colab에서 실행

[Colab 노트북 열기](https://colab.research.google.com/github/SKKUPhysicsKing/textbook-ocr-pipeline/blob/main/notebooks/Textbook_OCR_Colab.ipynb)

저장소가 공개되어 있으므로 별도의 GitHub 토큰 없이 열 수 있습니다. 직접 링크가 열리지 않으면 GitHub에서 `notebooks/Textbook_OCR_Colab.ipynb`를 다운로드한 뒤 Colab의 **File → Upload notebook**으로 여세요. 노트북의 셀을 위에서부터 실행하고 이미지·PDF·ZIP을 업로드하면 결과 ZIP이 자동으로 다운로드됩니다.

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

`manifest.json`에는 입력 경로, OCR·전처리·레이아웃 설정, 페이지 수와 페이지별 평균 신뢰도가 기록됩니다. 페이지별 JSON에는 검출된 열 영역, 품질 경고, 단어 텍스트, 신뢰도와 원본 페이지 기준 좌표가 포함됩니다.

## 촬영 권장 조건

- 페이지와 카메라가 최대한 평행하도록 촬영합니다.
- 그림자가 글자 위를 지나가지 않도록 균일하게 조명합니다.
- 페이지 전체가 프레임 안에 들어오게 하고 글자가 흐려지지 않도록 초점을 고정합니다.
- 메신저 압축본 대신 카메라 원본을 사용하고, 2단 교재는 페이지 폭 1600 px 이상을 확보합니다.
- 수식, 표, 다단 편집은 일반 문장보다 오류가 많으므로 결과를 검수해야 합니다.

## 테스트

```bash
python -m unittest discover -s tests -v
```

촬영된 영문 2단 교재 3쪽을 사용한 표본 비교는 [OCR 평가 기록](docs/ocr-evaluation-20260902.md)에 정리되어 있습니다.

## 현재 한계

- 수식의 LaTeX 변환과 표 구조 복원은 아직 지원하지 않습니다.
- 곡면 페이지의 원근·왜곡 보정은 후속 기능입니다.
- Tesseract 언어 데이터 품질에 따라 한영 혼합 문서 정확도가 달라집니다.
- 자동 열 검출은 휴리스틱이므로 복잡한 레이아웃에서는 `--layout single` 또는 `--layout columns`로 직접 지정해야 할 수 있습니다.
