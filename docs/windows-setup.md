# Windows에서 처음부터 실행하기

이 문서는 Windows 10/11에서 PowerShell을 사용해 프로젝트 폴더를 만들고, Python 가상환경과 Tesseract를 설치한 뒤 첫 OCR을 실행하는 전체 과정을 설명합니다. 명령은 한 줄씩 복사해 실행하세요.

## 전체 순서

1. Python, Git, Tesseract 설치
2. 세 프로그램이 PowerShell에서 인식되는지 확인
3. GitHub 저장소를 개인 PC로 복제
4. 프로젝트 전용 Python 가상환경 생성·활성화
5. Python 패키지 설치
6. 테스트 실행
7. 교재 사진 또는 PDF를 넣고 OCR 실행

## 1. 필수 프로그램 설치

### 1-1. Python

1. [Python Windows 다운로드 페이지](https://www.python.org/downloads/windows/)를 엽니다.
2. Python 3.10 이상의 64-bit Windows 설치 프로그램을 받습니다. 특별한 이유가 없다면 최신 안정 버전을 사용하면 됩니다.
3. 설치 화면에서 **Add python.exe to PATH** 또는 이에 해당하는 PATH 추가 옵션이 보이면 체크합니다.
4. 기본 설치를 완료합니다.

설치 후 열려 있던 PowerShell 창은 모두 닫고 새 PowerShell을 엽니다.

### 1-2. Git for Windows

1. [Git for Windows 공식 다운로드 페이지](https://git-scm.com/downloads/win)를 엽니다.
2. 64-bit Git for Windows를 설치합니다.
3. 특별히 변경할 이유가 없다면 설치 옵션은 기본값을 유지합니다.

이 프로젝트는 공개 저장소이므로 복제할 때 GitHub 로그인은 필요하지 않습니다.

### 1-3. Tesseract OCR

Tesseract 프로젝트는 최신 Windows용 공식 설치 프로그램을 직접 배포하지 않으며, 공식 설치 문서에서 UB Mannheim의 Windows 빌드를 안내합니다.

1. [Tesseract 공식 Windows 설치 안내](https://tesseract-ocr.github.io/tessdoc/Installation.html#windows)를 엽니다.
2. 문서의 **Tesseract at UB Mannheim** 링크로 이동해 64-bit Tesseract 5 설치 프로그램을 받습니다.
3. 설치 위치는 기본값인 `C:\Program Files\Tesseract-OCR`을 권장합니다.
4. 언어 데이터 선택 화면에서 English와 Korean을 설치합니다. Korean의 언어 코드는 `kor`입니다.
5. PATH 추가 선택지가 있으면 체크합니다.

## 2. 설치 확인

시작 메뉴에서 **Windows PowerShell**을 검색해 일반 권한으로 실행합니다. 관리자 권한은 필요하지 않습니다.

아래 명령을 한 줄씩 실행합니다.

```powershell
git --version
py --version
tesseract --version
tesseract --list-langs
```

정상이라면 다음을 확인할 수 있습니다.

- `git version ...`
- `Python 3.x.x`
- `tesseract 5.x.x`
- 언어 목록에 `eng`와 `kor`

### `tesseract`가 인식되지 않을 때

먼저 파일 탐색기에서 다음 파일이 존재하는지 확인합니다.

```text
C:\Program Files\Tesseract-OCR\tesseract.exe
```

파일이 있다면 Windows 검색에서 **환경 변수 편집**을 열고 다음 순서로 PATH를 등록합니다.

1. **사용자 변수**의 `Path` 선택
2. **편집** 선택
3. **새로 만들기** 선택
4. `C:\Program Files\Tesseract-OCR` 입력
5. 모든 창에서 확인
6. PowerShell을 완전히 닫고 다시 실행

그다음 다시 실행합니다.

```powershell
tesseract --version
tesseract --list-langs
```

### `kor`가 없을 때

다음 파일이 있는지 확인합니다.

```text
C:\Program Files\Tesseract-OCR\tessdata\kor.traineddata
```

없다면 Tesseract 설치 프로그램을 다시 실행해 Korean language data를 추가하는 방법이 가장 간단합니다. 수동 설치가 필요하면 [Tesseract 공식 tessdata 저장소](https://github.com/tesseract-ocr/tessdata_fast/blob/main/kor.traineddata)의 `kor.traineddata`를 받아 위 `tessdata` 폴더에 넣습니다. `Program Files`에 복사할 때는 관리자 승인이 필요할 수 있습니다.

## 3. 프로젝트 폴더 생성 및 저장소 복제

사용자 홈 폴더 아래에 `Projects` 폴더를 만들겠습니다. PowerShell에서 다음을 실행합니다.

```powershell
cd $env:USERPROFILE
New-Item -ItemType Directory -Force Projects
cd Projects
```

GitHub 저장소를 복제합니다.

```powershell
git clone https://github.com/SKKUPhysicsKing/textbook-ocr-pipeline.git
cd textbook-ocr-pipeline
```

공개 저장소이므로 GitHub 로그인 없이 복제할 수 있습니다.

현재 폴더가 맞는지 확인합니다.

```powershell
Get-Location
Get-ChildItem
```

목록에 `README.md`, `pyproject.toml`, `src`, `tests`가 보이면 정상입니다.

### `Repository not found`가 표시될 때

- 브라우저에서 `https://github.com/SKKUPhysicsKing/textbook-ocr-pipeline`가 열리는지 확인합니다.
- 저장소 주소를 오타 없이 복사했는지 확인합니다.
- 회사나 학교 네트워크에서 GitHub 접속이 차단되지 않았는지 확인합니다.

Git 명령이 계속 어렵다면 GitHub 저장소 페이지의 **Code → Download ZIP**으로 내려받고 `%USERPROFILE%\Projects`에 압축을 풀어도 실행할 수 있습니다. 다만 이 방법은 이후 `git pull`로 자동 업데이트할 수 없습니다.

## 4. Python 가상환경 생성

반드시 `textbook-ocr-pipeline` 폴더 안에서 실행합니다.

```powershell
py -m venv .venv
```

생성된 가상환경을 활성화합니다.

```powershell
.\.venv\Scripts\Activate.ps1
```

성공하면 PowerShell 명령줄 왼쪽에 `(.venv)`가 표시됩니다.

```text
(.venv) PS C:\Users\사용자이름\Projects\textbook-ocr-pipeline>
```

실제로 가상환경의 Python을 사용 중인지 확인합니다.

```powershell
python -c "import sys; print(sys.executable)"
```

출력 경로 끝이 다음과 같아야 합니다.

```text
textbook-ocr-pipeline\.venv\Scripts\python.exe
```

### `Activate.ps1 cannot be loaded` 오류

PowerShell의 스크립트 실행 정책 때문에 발생할 수 있습니다. 다음 명령은 현재 Windows 사용자에게만 로컬 스크립트 실행을 허용합니다.

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

확인 질문이 나오면 `Y`를 입력한 뒤 다시 활성화합니다.

```powershell
.\.venv\Scripts\Activate.ps1
```

정책을 변경하고 싶지 않다면 가상환경을 활성화하지 않고 다음처럼 가상환경 Python의 전체 경로를 직접 사용해도 됩니다.

```powershell
.\.venv\Scripts\python.exe -m pip install -e .
```

## 5. 프로젝트 설치

명령줄 앞에 `(.venv)`가 있는 상태에서 실행합니다.

```powershell
python -m pip install --upgrade pip
python -m pip install -e .
```

`-e .`는 현재 폴더의 프로젝트를 가상환경에 연결해 설치한다는 뜻입니다. 설치가 끝나면 다음 명령을 확인합니다.

```powershell
textbook-ocr --help
```

도움말이 나타나면 설치가 완료된 것입니다.

## 6. 테스트 실행

```powershell
python -m unittest discover -s tests -v
```

마지막에 다음과 비슷하게 표시되어야 합니다.

마지막 줄에 `OK`가 표시되면 정상입니다. 테스트 개수는 프로젝트 업데이트에 따라 달라질 수 있습니다.

이 테스트는 파일 처리, TSV 파싱, 전처리와 2단 레이아웃 검출을 검사합니다. 실제 한국어 인식 가능 여부는 다음 명령으로 별도 확인합니다.

```powershell
tesseract --list-langs
```

## 7. 입력 폴더 만들기

프로젝트 폴더 안에 `input` 폴더를 만듭니다.

```powershell
New-Item -ItemType Directory -Force input
explorer .\input
```

열린 파일 탐색기 창에 교재 사진이나 PDF를 복사합니다. 지원 형식은 JPG, JPEG, PNG, TIFF, BMP, WebP, PDF입니다. 메신저 압축본 대신 카메라 원본을 사용하고, 2단 교재는 페이지 폭 1600 px 이상을 권장합니다. 파일은 촬영 순서대로 정렬될 수 있도록 다음과 같이 이름을 지정하는 것이 좋습니다.

```text
page_001.jpg
page_002.jpg
page_003.jpg
```

## 8. 첫 OCR 실행

`input` 폴더 전체를 처리하고 전처리된 이미지도 저장합니다.

```powershell
textbook-ocr ".\input" -o ".\output" --save-processed
```

기본값은 영문 교재에 맞춘 `eng`, 원본 보존 전처리(`raw`), 2단 자동 검출(`auto`)입니다. 실행 중 `low_resolution` 경고가 나오면 OCR은 계속되지만 원본 해상도가 낮다는 뜻입니다.

완료되면 결과 폴더를 엽니다.

```powershell
explorer .\output
notepad .\output\combined.txt
```

주요 결과는 다음과 같습니다.

- `output\combined.txt`: 모든 페이지를 합친 텍스트
- `output\manifest.json`: 실행 설정, 페이지 수, 신뢰도
- `output\pages\page_0001.txt`: 페이지별 텍스트
- `output\pages\page_0001.json`: 단어별 좌표와 신뢰도
- `output\processed\page_0001.png`: OCR에 사용한 전처리 이미지

### 이미지 한 장만 처리

```powershell
textbook-ocr ".\input\page_001.jpg" -o ".\output" --save-processed
```

### PDF 처리

```powershell
textbook-ocr ".\input\textbook.pdf" -o ".\output" --pdf-dpi 300
```

PDF가 너무 크거나 메모리가 부족하면 해상도를 낮춥니다.

```powershell
textbook-ocr ".\input\textbook.pdf" -o ".\output" --pdf-dpi 200
```

### 한글과 영어가 섞인 문서

```powershell
textbook-ocr ".\input" -o ".\output" --lang kor+eng --save-processed
```

### 2단 편집을 직접 지정

자동 검출이 실패하면 다음처럼 열 분리를 강제로 지정합니다.

```powershell
textbook-ocr ".\input" -o ".\output" --layout columns --column-psm 6 --save-processed
```

반대로 표나 그림 때문에 잘못 분리되면 단일 페이지 모드를 사용합니다.

```powershell
textbook-ocr ".\input" -o ".\output" --layout single --save-processed
```

### 전처리 비교

기본 `raw` 결과가 좋지 않을 때만 그레이스케일 또는 이진화를 비교합니다.

```powershell
textbook-ocr ".\input" -o ".\output-gray" --preprocess grayscale
textbook-ocr ".\input" -o ".\output-binary" --preprocess binary --threshold 170
textbook-ocr ".\input" -o ".\output-upscaled" --upscale-width 1600
```

## 9. 다음에 다시 실행할 때

PC를 재부팅하거나 PowerShell을 새로 열면 가상환경을 다시 활성화해야 합니다.

```powershell
cd "$env:USERPROFILE\Projects\textbook-ocr-pipeline"
.\.venv\Scripts\Activate.ps1
textbook-ocr ".\input" -o ".\output" --save-processed
```

작업이 끝난 뒤 가상환경에서 나가려면 다음을 실행합니다.

```powershell
deactivate
```

## 10. GitHub의 최신 코드로 업데이트

```powershell
cd "$env:USERPROFILE\Projects\textbook-ocr-pipeline"
git pull
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
python -m unittest discover -s tests -v
```

`.venv`, `input`, `output` 폴더는 GitHub에 업로드되지 않도록 설정되어 있습니다.

## 자주 발생하는 오류

### `py` 또는 `python`을 찾을 수 없음

Python 설치 후 PowerShell을 새로 열었는지 확인합니다. 그래도 안 되면 Python을 다시 설치하면서 PATH 추가 옵션을 체크합니다.

### `No module named ...`

가상환경이 활성화되지 않았거나 패키지 설치가 누락된 상태입니다.

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

### `textbook-ocr`을 찾을 수 없음

먼저 명령줄 앞에 `(.venv)`가 있는지 확인합니다. 없으면 가상환경을 활성화합니다. 그래도 안 되면 다음 방식으로 직접 실행할 수 있습니다.

```powershell
python -m textbook_ocr ".\input" -o ".\output" --save-processed
```

### `Missing Tesseract language data: kor`

`tesseract --list-langs`에 `kor`가 없습니다. `kor.traineddata`가 `C:\Program Files\Tesseract-OCR\tessdata`에 있는지 확인합니다.

### 결과가 비어 있거나 정확도가 낮음

1. 먼저 `output\processed`의 전처리 이미지를 확인합니다.
2. 사진의 초점, 그림자, 반사광과 페이지 기울기를 확인합니다.
3. 글자가 사라질 정도로 이진화되었다면 자동 이진화를 끄는 기능은 아직 없으므로 원본의 밝기와 대비를 조절해 다시 촬영합니다.
4. 수식, 표와 다단 편집은 일반 문장보다 인식 오류가 많습니다.

## 개인정보와 파일 처리 위치

이 프로젝트는 Tesseract를 PC에서 직접 실행합니다. 사진과 PDF가 Google이나 별도의 OCR 서버로 자동 전송되지 않습니다. GitHub에는 프로그램 코드만 있으며 `input`과 `output` 폴더는 `.gitignore`로 제외됩니다.
