# 폴더 이미지 → Director 이미지 1 → Ollama 자동 연동

ComfyUI를 재시작하고 브라우저를 새로고침한 뒤 사용합니다.

1. `Load Image List From Dir (Inspire)`의 `directory`에 이미지 폴더를 입력합니다.
2. `FILE PATH` 출력을 Director의 `external_image_1_path`에 연결합니다. `IMAGE` 출력이 아닙니다.
3. Writer의 `link_to_director`를 켜고 `mode=FOLLOW_DIRECTOR`를 사용합니다.
4. Director의 이미지 1은 목록의 현재 파일로 대체됩니다. 이미지 2 이후와 음성 레퍼런스는 유지됩니다.
5. 실행 시 같은 경로가 Writer에도 전달됩니다. Writer로 가는 추가 선은 필요 없습니다.

`start_index`는 시작 위치(0부터), `image_load_cap`은 읽을 수량(0은 전체)입니다.
예: `start_index=0`, `image_load_cap=2`이면 첫 두 이미지가 각각 처리됩니다.

외부 경로를 연결하지 않으면 기존 Director 업로드 방식 그대로 동작합니다.
연결 중에는 Director의 기존 이미지 1 미리보기가 자동 교체되지 않습니다.
실제 사용한 파일은 Writer report의 `External image 1`에서 확인합니다.

자동 연동 중에는 Writer의 `first_frame` / `last_frame` / `ref_images` 수동 연결을
해제하고 추가 레퍼런스를 Director에 넣습니다. 서로 다른 이미지가 양쪽에 들어가는
것을 막기 위한 검사입니다. 여러 Director를 공유하는 Writer에는 `director_node_id`를
지정합니다. Prompt Freeze는 저장된 프롬프트 사용 모드가 아닌 실시간 전달 상태여야
이미지마다 새 프롬프트를 작성합니다.

Inspire는 선택한 파일들을 먼저 목록으로 읽습니다. 이 패치는 디스크에서 한 장씩
지연 로딩하는 큐 기능이 아닙니다. ComfyUI의 리스트 실행을 사용하므로 전체 파이프라인의
메모리 사용과 최종 저장 단위는 뒤쪽 노드 설정에도 달려 있습니다. 처음에는 cap=2로
확인하세요. 생성 길이, 해상도, seed, 체인 설정은 이 패치가 바꾸지 않습니다.

API를 직접 호출할 때는 Director와 Writer 양쪽의 `external_image_1_path`에 동일한
상위 노드의 FILE PATH 링크를 넣어야 합니다. 브라우저 확장이 실행 그래프에 이 연결을
추가하므로 저장된 워크플로우에는 Writer로 향하는 자동 선이 표시되지 않습니다.

검증: Python 단위/통합 테스트와 프런트엔드 실행 그래프 연결 테스트. 실제 H3 영상
생성과 Ollama 응답 품질은 이 테스트에 포함하지 않았습니다.
