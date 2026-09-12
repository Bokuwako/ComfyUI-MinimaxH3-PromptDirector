# ComfyUI-MinimaxH3-PromptDirector

> ### ⚠️ 성인용 도구입니다 / Adult content notice
>
> 이 저장소는 영상 생성용 **텍스트 프롬프트 작성 도구**입니다. 이미지나 영상은
> 들어 있지 않습니다. 다만 `mmh3/acts.py` 의 자세 어휘에는 **성행위를 가리키는
> 해부학적 영어 용어**가 들어 있습니다. 미성년자는 사용하지 마세요.
>
> This repository is a **text prompt-authoring tool** for video generation. It
> contains no images or video. The pose vocabulary in `mmh3/acts.py` does include
> **anatomical English terms for sexual acts**. Not intended for minors.
>
> 이 도구로 만든 결과물에 대한 책임은 사용자에게 있습니다. 실존 인물을 대상으로
> 하거나 미성년자로 보이는 대상을 성적으로 묘사하는 데 쓰지 마세요. 사용하는
> 영상 모델과 서비스의 약관을 확인하세요.

MiniMax H3 (DaSiWa `MiniMaxH3Director`) 용 **Ollama 기반 프롬프트 생성기**.

자연어 한 줄 + 스타일 프리셋 + (선택) 레퍼런스 이미지 → `VIDEO_PROMPT_WRITING_GUIDE` 규격에
정확히 맞는 영어 프롬프트를 만들어 `external_prompt_overwrite` 로 바로 흘려보냅니다.

```
[MMH3 Prompt Writer (Ollama)] --prompt--> [MiniMaxH3Director].external_prompt_overwrite
```

---

### v2 에서 새로 생긴 것

| | |
|---|---|
| 📚 **에셋 라이브러리** | 배우·의상·장소·소품·레이아웃·목소리를 이름으로 저장해 두고 다른 워크플로우에서 불러 씁니다. 노드 2개 + 전체 화면 관리 패널 |
| 🎭 **테마 (장르)** | 스타일과 **따로** 고릅니다. 스타일이 매체를, 테마가 장르를 정합니다 — `2D 애니` + `그라비아 화보` = 애니 화보 |
| ✂️ **샷 연결 방식** | 컷 뒤의 샷이 앞 샷과 어떤 관계인지 고릅니다. 컷마다 배경이 바뀌던 문제가 여기서 해결됩니다 |
| ⏱️ **대사 길이 검사** | 러닝타임에 대사가 안 들어가면 경고합니다. 일본어·한국어는 글자 수로 셉니다 |
| 🔒 **Prompt Freeze 편집이 실제로 편집을 합니다** | 편집 가이드라인을 11,349자 → 1,721자로 줄였습니다. 길었을 때는 모델이 편집 대신 새로 썼습니다 |

자세한 내용과 고친 것들은 **[CHANGELOG.md](CHANGELOG.md)** 에 있습니다.
파이썬이 바뀌었으므로 업데이트 후 **ComfyUI 재시작**이 필요합니다.

---

## 0. 30초 사용법

1. `custom_nodes` 에 폴더를 넣고 **ComfyUI 재시작**
2. 터미널에서 `ollama serve` 실행 + `ollama pull qwen2.5vl:7b`
3. 캔버스 더블클릭 → **`MiniMax H3 Prompt Writer (Ollama)`** 추가
4. 그 노드의 **`prompt`** 출력을 → **`MiniMax H3 Director`** 의 **`external_prompt_overwrite`** 입력에 연결
   (연결선은 이거 하나면 끝. Preview 노드는 없어도 됩니다)
5. 노드에서 딱 두 개만 만지기:
   - **`brief`** — 만들고 싶은 걸 한국어로 그냥 씀
   - **`style`** — 실사 / 2D 애니 / 3D 등 고르기
6. **Run**

나머지는 다 기본값 그대로 두세요. 모드(T2VA·I2VA·FL2VA·REF2VA), 길이, 레퍼런스 이미지는
**Director에서 평소 하던 대로** 설정하면 이 노드가 알아서 따라갑니다.

> ⚠️ **버전을 올릴 때는 캔버스의 노드를 삭제하고 다시 추가하세요.**
> ComfyUI는 위젯 값을 이름이 아니라 **순서**로 복원하기 때문에, 위젯이 추가/변경되면
> 값이 한 칸씩 밀립니다 (`director_node_id = false`, `custom_style = true` 같은 증상).
> 코드에서 그런 쓰레기 값은 무시하도록 막아뒀지만, 다시 추가하는 게 확실합니다.

> ⚠️ **이미지를 쓰려면 반드시 비전 모델**이어야 합니다. `gemma`, `llama3`, `qwen3` 같은
> 텍스트 전용 모델을 고르면 이미지를 못 보고 **없는 내용을 지어냅니다.**
> 이제 그런 경우 실행을 멈추고 알려줍니다. `ollama pull qwen2.5vl:7b`

---

## 1. 설치

```bash
cd ComfyUI/custom_nodes
git clone <이 폴더>  ComfyUI-MinimaxH3-PromptDirector
# 또는 zip 압축을 custom_nodes/ComfyUI-MinimaxH3-PromptDirector 로 풀기
pip install -r ComfyUI-MinimaxH3-PromptDirector/requirements.txt
```

ComfyUI 재시작.

### Ollama 준비

```bash
ollama serve                    # 백그라운드 실행 중이어야 함
ollama pull qwen2.5vl:7b        # 이미지 입력을 쓸 거라면 '비전' 모델 필수
# 텍스트 전용(T2VA)만 쓸 거면 아무 모델이나:  ollama pull qwen3:8b
```

**이미지(I2VA·FL2VA·L2VA·REF2VA)를 쓸 때 쓸 만한 비전 모델**

| 모델 | 크기 | 비고 |
|---|---|---|
| `qwen2.5vl:7b` | ~6GB | 가장 무난. 이 용도에 충분 |
| `gemma4:12b` | 7.6GB | Gemma 계열 비전. 128K 컨텍스트 |
| `gemma4:26b` | 18GB | MoE(활성 3.8B). VRAM 여유 있으면 |
| `gemma4:e4b` | 9.6GB | 엣지용. 비전 + 오디오 |
| `llama3.2-vision:11b` | ~8GB | |
| `gemma3:12b` | 8.1GB | 구세대지만 안정적 |

Gemma 4는 **전 사이즈가 비전을 지원**합니다(e2b·e4b·12b·26b·31b).
Gemma 3는 `4b` / `12b` / `27b` 만 비전이고 `1b` · `270m` 은 텍스트 전용입니다.

> ⚠️ **커뮤니티 리팩(uncensored, VRAM-optimized 등)은 비전 타워(mmproj)가 제거된 경우가 많습니다.**
> 확인 방법: `ollama show <모델명>` → **Capabilities** 에 `vision` 이 있는지 보세요.
> 없으면 이미지를 못 봅니다. 이 노드도 같은 방법으로 검사해서 미리 막아줍니다.

ComfyUI와 Ollama가 다른 PC라면 노드의 `ollama_url` 을 `http://192.168.x.x:11434` 로 바꾸고,
Ollama 쪽에서 `OLLAMA_HOST=0.0.0.0` 로 띄우세요.

> 모델 드롭다운은 ComfyUI 시작 시점에 `/api/tags` 로 실제 설치 목록을 읽어옵니다.
> 목록에 없으면 `model_override` 텍스트칸에 태그를 직접 적으면 그 값이 우선합니다.

---

## 2. 노드 10개

**Prompt Writer 하나만 있어도 돌아갑니다.** 나머지는 필요할 때 붙이세요.

### 프롬프트 만들기

| 노드 | 하는 일 |
|---|---|
| 🎬 **MiniMax H3 Prompt Writer (Ollama)** | 메인. 자연어 → 규격 프롬프트. Director의 `external_prompt_overwrite` 로 직결 |
| 🎬 **MiniMax H3 Shot Builder** | 샷 카드 편집기. 샷마다 내용·행위·추가 동작·전개·대사·카메라를 쌓아 브리프를 만들어 Writer 에 넘깁니다 |
| 🎬 **MiniMax H3 Shot Settings** | 위 카드의 전역 설정 — 화풍·**테마(장르)**·영상 길이, 전개(progression) 개수·시드·대상, 대사 언어 |
| 🎬 **MiniMax H3 Style Directive** | 스타일 프리셋의 영어 지시문을 텍스트로 꺼내기 |

Shot Builder 는 브리프를 **자연어 한 줄로 못 쓰는 것**을 위해 있습니다 — 두 사람의
자세, 누가 움직이는지, 카메라가 누구 시점인지 같은 것들요. 안 쓰셔도 됩니다. Writer
의 `brief` 칸에 한국어로 쓰는 쪽이 잘 맞는 장면도 많습니다.

### 확인·디버깅

| 노드 | 하는 일 |
|---|---|
| 🎬 **MiniMax H3 Prompt Validator** | 모델 호출 없이 프롬프트 규격만 검사·자동수리 (오프라인) |
| 🎬 **MiniMax H3 Image Describe (Ollama)** | VLM이 레퍼런스 이미지를 실제로 뭐라고 읽는지 확인용 |

### 유틸

| 노드 | 하는 일 |
|---|---|
| 🔒 **MiniMax H3 Prompt Freeze** | 통과한 프롬프트를 칸에 담아둡니다. 위쪽 Writer 를 뮤트(Ctrl+M)하면 담아둔 걸 그대로 내보내서 **LLM 을 다시 안 돌립니다.** 프롬프트가 확정된 뒤 영상만 여러 번 뽑을 때 씁니다 |
| ☠️ **Unload Everything (Kill Switch)** | Clear VRAM 이 못 건드리는 것까지 전부 내립니다 — 격리된 워커 프로세스, Ollama 모델, ComfyUI 캐시. VRAM 이 안 빠질 때 |

> **Prompt Freeze 가 필요한 이유:** 시드를 고정해도 소용없습니다. 시드는 *무엇이 나오는지*
> 를 정할 뿐이고, ComfyUI 노드 캐시는 메모리에만 있어서 재시작하면 사라집니다. 그러면
> 같은 설정이어도 LLM 이 매번 처음부터 다시 돕니다.

### 에셋 <sup>v2</sup>

| 노드 | 하는 일 |
|---|---|
| 📚 **MiniMax H3 Asset Save** | 이미지를 이름 붙여 라이브러리에 저장합니다. 같은 이름으로 또 저장하면 파일이 덧붙고, 배치로 넣으면 `이름_00`, `이름_01` 로 갈립니다 |
| 📚 **MiniMax H3 Asset Load** | 저장해 둔 에셋을 드롭다운에서 골라 꺼냅니다. `file_key` 를 비워 두면 역할 우선순위대로 알아서 고릅니다 |

배우(actors) · 의상(costumes) · 장소(scenes) · 소품(props) · 레이아웃(layouts) ·
목소리(voices) 여섯 종류입니다. 노드에 달린 **📚 버튼**을 누르면 전체 화면 관리
패널이 열려서 이름 변경·삭제·폴더 열기를 할 수 있고, 바꾼 내용이 노드 드롭다운에
바로 반영됩니다.

배우 에셋은 그림이 여러 장일 때 `fullbody_threeview` → `bust_threeview` →
`asset_sheet` → `master` 순으로 골라 씁니다 — 전신 삼면도가 있으면 그걸 먼저 씁니다.

---

## 3. 메인 노드 사용법

### 3.1 연결 — 연결선은 딱 하나

```
[MMH3 Prompt Writer] --prompt--> [MiniMaxH3Director].external_prompt_overwrite
```

이게 전부입니다. `link_to_director = True`(기본값)이면 나머지는 **Director 노드에서 직접 읽어옵니다.**

| Director에서 읽어오는 것 | 결과 |
|---|---|
| `mode` 위젯 | Writer의 모드가 자동으로 따라감 |
| `duration` 위젯 | Writer의 `duration` 을 `0` 으로 두면 이 값을 사용 |
| **미디어 레인에 올린 이미지** | 슬롯 순서대로 읽어서 Ollama 비전 모델에 그대로 전달 |
| 이미지별 media prompt | 있으면 참고 정보로 함께 전달 |

즉 **Director에서 이미지를 갈아끼우고 모드만 바꾸면**, 프롬프트가 알아서 그 모드 규격으로 다시 써집니다.
Writer 쪽 IMAGE 입력은 연결할 필요 없습니다.

> 원리: ComfyUI가 실행 시 모든 노드에 넘겨주는 그래프(`PROMPT`)에서 `MiniMaxH3Director` 를 찾아
> `mode` / `duration` / `timeline_data` 위젯을 읽습니다. `timeline_data` 안의 파일명을
> ComfyUI의 `input` / `output` / `temp` 폴더에서 찾아 로드합니다.
> Director의 위젯이 바뀌면 캐시도 자동으로 무효화됩니다.
>
> 그래프에 Director가 **2개 이상**이면 `director_node_id` 에 대상 노드 id를 적어주세요.

### 3.2 모드 결정 규칙

**`mode = FOLLOW_DIRECTOR` (기본값)** — Director의 mode 위젯을 따릅니다.

| Director의 mode | 결정되는 모드 | 쓰이는 이미지 |
|---|---|---|
| `T2VA` | **T2VA** | 없음 (레인에 이미지가 있어도 무시) |
| `I2VA` | **I2VA** | 슬롯 0 → `<Picture 1>` |
| `FL2VA` / `FLF2VA` | 이미지 2장↑ → **FL2VA** | 첫 슬롯 → Picture 1, 마지막 슬롯 → Picture 2 |
| `FL2VA` / `FLF2VA` | 이미지 1장 → **I2VA** | 슬롯 0 |
| `FL2VA` / `FLF2VA` | 이미지 0장 → **T2VA** | 없음 |
| `REF2VA` | **REF2VA** | 슬롯 순서대로 최대 9장(`max_ref_images`) · 6섹션 확장 포맷 |

**`mode = AUTO`** — Writer에 직접 연결한 IMAGE 입력으로 판별
(없음→T2VA, first만→I2VA, first+last→FL2VA, last만→L2VA, ref→REF2VA).

**그 외 값 지정** — 그 모드를 강제합니다. 이때도 Director 레인의 이미지를
**강제한 모드에 맞게 다시 골라서** 씁니다. (예: Director는 REF2VA인데 Writer에서 `L2VA` 를
고르면 → 마지막 슬롯 이미지 1장만 last frame으로 사용)

### 3.3 우선순위

| 항목 | 이기는 쪽 |
|---|---|
| 이미지 | Writer에 직접 연결한 `first_frame`/`last_frame`/`ref_images` > Director 레인 |
| 모드 | Writer의 `mode` 위젯(≠ FOLLOW_DIRECTOR) > Director의 mode |
| duration | Writer의 `duration`(≥1) > Director의 duration |

덮어쓰기가 일어나면 `report` 출력에 `[link] ... overrides the Director ...` 로 표시됩니다.

### 3.4 주요 위젯

| 위젯 | 설명 |
|---|---|
| `brief` | **자연어 명령어.** 한국어로 써도 됩니다. 출력 프롬프트는 항상 영어 |
| `style` | 스타일 12종 + Auto + Custom (아래 4장) |
| `link_to_director` | Director에서 mode·duration·이미지를 읽어올지 (기본 ON) |
| `mode` | `FOLLOW_DIRECTOR`(기본) / `AUTO` / 특정 모드 강제 |
| `duration` | `0` = Director의 duration 사용. 1 이상이면 그 값 강제 |
| `shot_count` | `0` = 모델이 알아서. 1~8 지정 가능 |
| `dialogue_mode` | `none` 대사 없음 / `auto` 필요하면 알아서 / `verbatim` 아래 대사를 그대로 |
| `dialogue_language` | 대사에 쓸 언어. **`auto`·`verbatim` 양쪽 모두 적용됩니다** |
| `dialogue_text` | `verbatim` 일 때만 사용. 여기 적은 문장이 `<d>[언어] ...</d>` 안에 **글자 그대로** 들어갑니다 (번역·수정 안 함) |
| `include_soundscape` / `include_music` | 끄면 해당 필드가 `N/A` 로 고정 |
| `temperature` | 0.5~0.7 권장. 낮추면 규격 준수↑ 표현력↓ |
| `llm_seed` | `0` = 매 실행마다 새로 생성. 1 이상이면 결과 고정(캐시됨) |
| `auto_fix` | 규격 자동수리 on/off (기본 on, 켜두는 걸 권장) |
| `force_english` | 한국어가 섞이면 재생성 → 번역 패스로 영어 강제 (기본 ON, 옵션 입력) |
| `max_ref_images` | REF2VA에서 보낼 최대 이미지 수 (기본 9 = H3 스펙 상한) |
| `picture_roles` | **이미지마다 역할 지정** (아래 3.47). 프레임 오용·정체성 누출을 막습니다 |
| `unload_after` | 생성 후 Ollama 모델을 VRAM에서 즉시 내림. H3 본체와 VRAM 경쟁할 때 켜세요 |

옵션 입력 `extra_directives` 에는 한 줄짜리 추가 규칙을 넣습니다 (최우선 적용).
예: `Keep the camera locked off. No cuts. The woman never faces the camera.`

### 3.47 picture_roles — 이미지마다 역할 지정

레퍼런스를 넣었을 때 나는 두 가지 고질병이 있습니다.

- **캐릭터 참조만 넣으면** H3가 레퍼런스의 그림체를 무시하고 자기 고정 화풍으로 그립니다.
- **자세·의상 참조를 추가하면** 그걸 영상의 **프레임**으로 써버리려 합니다.

둘 다 원인이 같습니다 — 프롬프트 어디에도 "이 이미지들은 영상의 프레임이 아니다"라는 말이
없고, 어느 이미지가 화풍 담당인지도 안 적혀 있기 때문입니다.

**노드에 버튼 세 개가 있습니다.**

| 버튼 | 동작 |
|---|---|
| `＋ 역할 추가` | 행 하나 추가 (비어 있는 이미지 번호를 자동으로 잡습니다) |
| `－ 마지막 행 삭제` | 맨 아래 행 제거 |
| `⌫ 전체 지우기` | 전부 제거 → 역할 미지정 상태로 |

행마다 **역할 드롭다운**과 **이미지 번호**를 고릅니다.
특정 행만 지우려면 그 행의 역할 드롭다운 맨 아래 `✕ 이 행 삭제` 를 고르세요.

고른 내용은 아래 `picture_roles` 텍스트칸에 이렇게 저장됩니다:

```
1: character
2: character
3: pose        # 앉은 자세만
4: background
5: style
```

**직접 타이핑해도 됩니다** — 텍스트칸이 원본이고 버튼 UI는 그걸 편집하는 도구일 뿐입니다.
`#` 뒤에 메모를 달 수 있는데, 이건 텍스트칸에서만 가능합니다.
한국어도 됩니다 — `캐릭터` · `배경` · `의상` · `자세` · `표정` · `동작` · `화풍` · `소품` ·
`구도` · `프레임`. `#` 뒤에는 메모를 답니다.

| 역할 | Subject 처리 | 마커 | 전이 금지 |
|---|---|---|---|
| `character` 캐릭터 | 독립 Subject | `fully_preserved` | — |
| `background` 배경 | 독립 Subject | `fully_preserved` | 그 안의 인물 |
| `costume` 의상 | 속성 Subject | `attribute_transfer` | 얼굴·머리·체형·배경 |
| `pose` 자세 | 속성 Subject | `attribute_transfer` | 얼굴·머리·의상·체형·배경 |
| `expression` 표정 | 속성 Subject | `attribute_transfer` | 정체성·자세·배경 |
| `motion` 동작 | 속성 Subject | `attribute_transfer` | 외모·의상·장소 |
| `style` 화풍 | 속성 Subject | `attribute_transfer` | 인물·사물·구도·장소 |
| `prop` 소품 | 독립 Subject | `fully_preserved` | 든 사람·배경 |
| `composition` 구도 | 속성 Subject | `attribute_transfer` | 인물·의상·장소·화풍 |
| `frame` 프레임 | **프레임 앵커** | `fully_preserved` | — |

**핵심은 두 문장입니다.**

`frame` 역할이 하나도 없으면 프롬프트에 이게 박힙니다:

> **NONE OF THESE PICTURES IS A FRAME OF THE TARGET VIDEO.** 어떤 이미지도 첫 프레임·
> 마지막 프레임·중간 프레임으로 재현하지 말 것. 구도·카메라 앵글·배경 배치도 복사하지 말 것
> (구도/배경 역할로 지정된 경우 제외). 작업 유형은 `reference generation` 이며 절대
> `keyframe completion` 이 아니다.

`style` 역할이 있으면:

> 영상의 화풍은 `<Picture N>` 에서 온다. `[Shot 1]` 을 그 화풍의 구체적 서술 — 선의 질감,
> 셰이딩 방식, 색 처리, 디테일 수준 — 으로 열 것. 일반적인 스타일 라벨로 때우지 말 것.

`frame` 역할을 지정하면 반대로 그 이미지만 프레임 앵커가 되고, 작업 유형에
`keyframe completion` 이 추가되며, 나머지는 여전히 프레임이 아니라고 못 박습니다.

지정을 안 하면 리포트에 `picture roles: none declared` 로 표시되고 모델이 알아서 판단합니다.

### 3.5 출력

| 출력 | 용도 |
|---|---|
| `prompt` | Director로 보낼 완성 프롬프트 |
| `mode` | 실제로 결정된 모드 문자열 |
| `report` | `[ok]` / `[fix]` / `[warn]` 로그 — PreviewAny에 연결해서 보세요 |
| `duration` | 그대로 통과 (Director에 같이 물려도 됨) |
| `raw` | 자동수리 전의 모델 원문 (프롬프트가 이상할 때 원인 파악용) |

---

## 4. 스타일 프리셋 12종

`mmh3/styles.json` 에 정의돼 있습니다. 기존 항목의 **내용**을 고치면 다음 실행부터 즉시 반영되고,
**항목을 새로 추가**했을 때는 브라우저를 새로고침(F5)해야 드롭다운에 나타납니다.

**핵심 6종**

| # | 프리셋 | style line |
|---|---|---|
| 01 | 실사 | `Live-action, cinematic` |
| 02 | 반실사 | `Semi-realistic stylized render, cinematic` |
| 03 | 3D CG 애니메이션 | `3D CG animation, feature-animation look` |
| 04 | 2D 재패니즈 애니 | `2D Japanese cel animation, anime` |
| 05 | 클레이·스톱모션 | `Claymation stop-motion` |
| 06 | 빈티지 필름·다큐 | `Vintage film, 16mm documentary look` |

**확장 6종**

| # | 프리셋 | style line |
|---|---|---|
| 07 | 수채화·잉크 | `Watercolour and ink illustration, animated` |
| 08 | 픽셀아트·레트로 게임 | `Pixel art, 16-bit retro game look` |
| 09 | 광고·제품 CF | `High-end commercial product film, live-action` |
| 10 | 뮤직비디오·네온 사이버펑크 | `Music-video look, neon cyberpunk, cinematic` |
| 11 | 웹툰·카툰 | `Webtoon-style 2D cartoon animation` |
| 12 | 미니어처·틸트시프트 | `Live-action tilt-shift miniature look` |

각 프리셋은 단순 키워드가 아니라 **7개 축**을 함께 강제합니다:
`style_line`(1샷 첫머리 고정) · `render`(질감) · `lighting`(조명) · `camera`(선호 카메라 무빙) ·
`motion`(움직임 성격) · `soundscape` / `music`(사운드 성향) · `avoid`(금지 요소).

- `00. Auto` — 자연어에서 스타일을 모델이 직접 판별
- `99. Custom` — `custom_style` 텍스트칸의 내용을 그대로 스타일로 사용 (첫 줄이 style line)

**나만의 스타일 추가:** `mmh3/styles.json` 에 같은 형식으로 항목을 하나 더 넣으면
드롭다운에 자동으로 나타납니다.

---

## 4.2 테마 (장르) 16종 <sup>v2</sup>

`mmh3/themes.json`. Shot Settings 에서 스타일 **바로 아래**에 있습니다.

**스타일이 매체를, 테마가 장르를 정합니다.** 둘은 같이 씁니다 —
`2D 재패니즈 애니` + `그라비아 화보` 는 애니 화보가 됩니다.

| | | | |
|---|---|---|---|
| 그라비아 화보 | 감성 포트레이트 | 패션 룩북 | 시네마틱 드라마 |
| 일상 | 브이로그 | 다큐멘터리 | 호러 / 서스펜스 |
| 느와르 / 스릴러 | 액션 | 판타지 / 이세계 | 사이버펑크 네온 |
| SF | 뮤직비디오 | 광고 / 제품 CF | 여행 필름 |

기본값은 `없음` 입니다. 고르면 브리프 앞에 **장르 이름 한 줄**만 들어가고,
조명·구도·의상·소품은 모델이 그 장르 지식대로 고릅니다.

> 예전에는 장르마다 조명·구도·의상 표와 장면 예시 15개를 손으로 적어 넣었습니다.
> 테스트해 보니 27B 모델이 그 표보다 훨씬 많이 알고 있었습니다 — 역광과 림라이트,
> 프레임 인 프레임, 반사 구도, 렌즈와 조리개, 계절별 경향까지 스스로 말했고,
> 장소·의상·빛이 서로 어울리는 컨셉도 한 번에 만들었습니다. **표는 그 지식을
> 대체한 게 아니라 덮고 있었습니다.** 그래서 이름만 남겼습니다.

---

## 4.5 REF2VA 6섹션 규격

공식 `VIDEO_PROMPT_WRITING_GUIDE_ref_en.md` 를 따릅니다.

```
integrated_multimodal_description: subject_definitions:
<Subject 1> is the girl whose face and halo come from <Picture 1> and whose blazer
and bag come from <Picture 2> — short grey hair, cat ears, blue eyes, ...
<Subject 2> is the downhill forest road environment in <Picture 3>, featuring ...

summary:
[reference generation] A 5-second 2D Japanese cel animation in which <Subject 1>
coasts down the sloping road of <Subject 2>.

retention_analysis:
<Subject 1> (appears in [Shot 1]): fully_preserved - the grey hair, cat ears, blue
eyes and glowing halo are retained without change.
<Subject 2> (appears in [Shot 1]): partially_preserved - road and treeline kept.

detailed_description:
[Shot 1] 2D Japanese cel animation, anime, a locked-off side view of <Subject 2>. ...

overall_soundscape: ...

non_diegetic_music: ...
```

**`<Subject N>` 은 파일이 아니라 "화면에 나올 내용 단위"입니다.**
사람·동물·사물뿐 아니라 **장면·배경·환경**, 의상·소품·인터페이스·시각효과,
스타일·동작·표정·포즈가 전부 Subject가 됩니다.

Subject와 Picture는 **1:1이 아닙니다.**

- 한 인물의 캐릭터 시트 3장 → **Subject 1개**가 picture 3장을 인용
- 인물과 방이 같이 찍힌 사진 1장 → **Subject 2개**를 정의할 수 있음

**모든 사진에 배역을 주세요.** 어느 것이 정체성 / 배경 / 의상 / 스타일 / 모션을
담당하는지 명시하는 편이 "이미지를 참고해"보다 훨씬 잘 먹힙니다.

**작업 유형** (summary 첫 대괄호): `reference generation` · `keyframe completion` ·
`video editing` · `video continuation` · `audio reuse` · `audio reference` (` + ` 로 조합)

**보존 마커** (retention_analysis):
시각 `fully_preserved` / `partially_preserved` / `attribute_transfer` / `weak_reference`
오디오 `fully_copy` / `partially_copy` / `reference` / `weak_reference`

검증기가 위 구조를 전부 검사합니다 — 하위 섹션 누락·순서, `<Subject N> is ...` 형식,
대괄호 작업유형, 보존 마커 유무, 그리고 **보내지도 않은 `<Picture N>` 인용**까지.

> H3는 이미지 9 · 영상 3 · 오디오 3 (합계 12)까지 받습니다. 이 노드는 이미지만 Ollama에
> 전달합니다. 영상·오디오 슬롯은 Director에 그대로 두면 H3가 직접 씁니다.

---

## 5. 자동수리(auto_fix)가 잡아주는 것

LLM은 규격을 반드시 흘립니다. `auto_fix` 는 **모델 호출과 무관한 결정론적 후처리**로 다음을 강제합니다.

수리(`[fix]`)

- ```` ``` ```` 코드펜스, `<think>` 추론 블록, "Sure! Here is..." 같은 앞뒤 잡담 제거
- 세 필드(`integrated_multimodal_description` / `overall_soundscape` / `non_diegetic_music`)를
  올바른 순서·빈 줄 1개 간격으로 재조립
- `[Shot 1]` 에 붙은 타임스탬프 제거 (규격상 1샷은 타임스탬프 없음)
- 샷 번호 재정렬 (1, 2, 3 … 빠짐/뒤바뀜 교정)
- 컷 타임스탬프가 없거나 · 역순이거나 · duration을 넘거나 · 0.8초 미만으로 붙어 있으면
  duration에 맞춰 균등 재분배
- 컷 문구(`the camera cuts to` 등)가 빠진 샷에 삽입
- 모드별 레퍼런스 정렬 지시문 첫 줄을 정확한 문장으로 삽입/교체 (T2VA·REF2VA면 제거)
- 빈 사운드 필드를 `N/A` 로

**영어 강제 (`force_english`, 기본 ON)** — 자동수리와 별개로 돌아갑니다.

`<d>...</d>` 안의 대사와 `"화면에 보이는 텍스트"` 를 **제외한** 모든 곳에 한글·일본어·한자·키릴 등이
남아 있으면:

1. **재생성** — 더 강한 언어 지시문 + temperature 를 0.35 이하로 낮춰서 한 번 더
2. 그래도 남으면 **번역 패스** — 구조([Shot n]·타임스탬프·화자 ID·필드명)는 그대로 두고
   설명문만 영어로 옮기는 전용 호출
3. 그래도 남으면 `[link] STILL non-English after 2 passes` 경고 (더 큰 모델 권장)

`<d>` 안의 한국어 대사와 간판의 `"영업중"` 같은 화면 텍스트는 **건드리지 않습니다.**
규격상 그건 원문 그대로여야 하기 때문입니다.

경고(`[warn]`, 자동수리 안 함 — 사람이 판단)

- `<d>` / `</d>` 개수 불일치, `[언어]` 태그 누락
- 보이스오버 뒤 `lips remain completely closed` 문장 누락
- `dialogue_mode=none` 인데 대사가 들어감
- (`force_english` 를 끈 경우만) `<d>` 와 `"..."` 밖에 한글/일본어/한자가 새어나옴
- `<d>[Japanese]` 태그인데 내용이 한국어인 식의 **언어 태그/문자 불일치**
- `non_diegetic_music` 에 추상적 감정어(`haunting`, `evoking`, `nostalgic` …) 사용
- 샷당 0.8초 미만이 되는 과도한 `shot_count`

---

## 6. 워크플로우 팁

- **VRAM**: H3 본체가 크므로 Ollama 모델은 7B급이면 충분합니다. `unload_after` 를 켜두면
  프롬프트 생성 직후 VRAM을 반납합니다.
- **재현성**: `llm_seed` 를 1 이상으로 두면 같은 입력 → 같은 프롬프트(ComfyUI가 캐시).
  매번 다른 결과를 원하면 `llm_seed = 0`.
- **프롬프트 검수 루프**: `raw` 와 `report` 를 `PreviewAny` 에 물려두고,
  `[warn]` 이 반복되는 항목이 있으면 `extra_directives` 에 규칙을 한 줄 추가하세요.
- **REF2VA**: 캐릭터 일관성이 핵심이므로 `subject_definitions` 가 길수록 좋습니다.
  결과가 부실하면 `Image Describe` 노드로 먼저 캡션을 뽑아 `extra_directives` 에 붙여넣으세요.
- **duration 불일치가 1순위 사고 원인**입니다. `duration = 0` 으로 두고 Director를 따라가게 하는 걸 권장합니다.
- **Director 레인 이미지를 바꿨는데 반영이 안 될 때**: `report` 의 첫 줄
  `[link] Director #NN: mode=... images=N` 을 확인하세요. 여기 안 잡히면 파일을 못 찾은 겁니다.

---

## 7. 파일 구조

```
ComfyUI-MinimaxH3-PromptDirector/
├── __init__.py                 노드 등록 (10개)
├── routes.py                   ★ 에셋 라이브러리 HTTP 라우트
├── requirements.txt
├── README.md  ·  CHANGELOG.md  ·  LICENSE
├── nodes/
│   ├── prompt_writer.py        Prompt Writer · Validator · Image Describe · Style Directive
│   ├── shot_builder.py         Shot Builder — 샷 카드를 브리프로
│   ├── shot_settings.py        Shot Settings — 화풍·테마·길이·전개 전역 설정
│   ├── prompt_freeze.py        Prompt Freeze — 확정된 프롬프트 재사용 + 편집
│   ├── assets.py               ★ Asset Save / Asset Load
│   └── kill_switch.py          Kill Switch — 전부 언로드
├── mmh3/
│   ├── director_link.py        ★ Director 노드 상태(mode/duration/이미지) 읽기
│   ├── guideline.py            가이드라인 → 시스템 프롬프트
│   ├── shotcards.py            샷 카드 어휘 + 브리프 조립 (시점·카메라·레퍼런스 역할·샷 연결)
│   ├── acts.py                 ★ 자세 어휘 + 전개(progression)
│   ├── shotlist.py             렌즈·조명·연기 톤 등 연출 어휘
│   ├── library.py              ★ 에셋 저장소 (배우·의상·장소·소품·레이아웃·목소리)
│   ├── roles.py  ·  genres.json
│   ├── styles.json             ★ 스타일 12종 (여기를 고치면 됨)
│   ├── styles.py               스타일 로더
│   ├── themes.json             ★ 테마(장르) 16종
│   ├── themes.py               테마 로더
│   ├── vision.py               이미지 → 묘사 (역할별로 물어볼 항목을 줄임)
│   ├── ollama_client.py        Ollama HTTP + IMAGE→base64
│   └── validator.py            규격 검사·자동수리 + 대사 길이 검사
├── web/                        Shot Builder · Prompt Freeze · picture_roles · 에셋 패널의 UI
├── docs/
│   └── AI_BRIEFING.md          다른 AI에게 Shot Builder 입력을 대신 설계시키는 문서
└── example_workflows/
    └── mmh3_prompt_writer_example.json
```

---

## 8. 문제 해결

| 증상 | 원인 / 해결 |
|---|---|
| `Cannot reach Ollama at ...` | `ollama serve` 미실행, 또는 `ollama_url` 오타 / 방화벽 |
| 모델 드롭다운이 비어 보임 | ComfyUI 시작 시 Ollama가 꺼져 있었음. Ollama 켜고 ComfyUI 재시작, 또는 `model_override` 에 직접 입력 |
| 이미지를 넣었는데 무시됨 | 비전 모델이 아님. `qwen2.5vl`, `llama3.2-vision`, `minicpm-v`, `llava` 계열 사용 |
| `report` 에 `Could not locate 'xxx.png'` | Director 레인의 파일이 input/output/temp 밖에 있음. ComfyUI에 다시 업로드하세요 |
| `No MiniMaxH3Director found in the graph` | Director 노드가 bypass/뮤트 상태거나 그래프에 없음 |
| `director_node_id 'false' matched nothing` | 워크플로우를 업그레이드하면서 위젯 값이 밀린 것. **노드를 삭제하고 다시 추가**하세요. (Director가 하나뿐이면 자동으로 그걸 쓰고 넘어갑니다) |
| `is a TEXT-ONLY model` | 선택한 Ollama 모델이 이미지를 못 봅니다. `ollama pull qwen2.5vl:7b` 후 `model` 에서 선택 |
| Director를 고쳤는데 프롬프트가 그대로 | `link_to_director` 가 꺼져 있거나 `mode`/`duration` 위젯이 수동값으로 덮고 있음 — `report` 확인 |
| 프롬프트에 한국어가 섞임 | `force_english` 가 ON이면 자동으로 재생성·번역합니다. `report` 에 `STILL non-English` 가 뜨면 `qwen2.5vl:32b` 등 더 큰 모델을 쓰세요 |
| 대사가 멋대로 번역됨 | `dialogue_mode` 를 `verbatim` 으로 두고 `dialogue_text` 에 원문을 넣으세요 |
| `[Japanese]` 태그인데 한국어가 나옴 | `auto` 모드는 모델이 대사를 지어내므로 작은 모델에선 언어가 흔들립니다. `report` 에 `dialogue language mismatch` 경고가 뜹니다. 확실하게 하려면 `verbatim` + `dialogue_text` 에 직접 입력 |
| 컷이 너무 빨리 지나감 | `shot_count` 를 줄이거나 `duration` 을 늘리세요 |
| 📚 버튼을 눌러도 패널이 안 열림 / 목록이 빔 <sup>v2</sup> | `routes.py` 는 ComfyUI 서버가 뜰 때 등록됩니다. 업데이트 후 **ComfyUI를 재시작**하고 브라우저를 새로고침(F5)하세요 |
| Prompt Freeze 로 편집했는데 결과가 입력과 똑같음 <sup>v2</sup> | 경고로 알려줍니다. 요청이 너무 추상적이면 모델이 손을 못 댑니다 — 어느 샷의 무엇을 어떻게 바꿀지 지정하세요 |
| 편집했더니 `summary` 만 바뀌고 샷 본문은 그대로 <sup>v2</sup> | 이것도 경고로 잡힙니다. `summary` 와 `retention_analysis` 는 본문을 **보고하는** 자리라, 본문이 안 바뀌면 바뀐 게 없는 것입니다 |
| 대사가 뭉개져서 발음됨 <sup>v2</sup> | `report` 의 `[warn] 대사 길이` 를 보세요. 일본어·한국어는 초당 4.5자가 한계입니다 — 대사를 줄이거나 `duration` 을 늘리세요 |
