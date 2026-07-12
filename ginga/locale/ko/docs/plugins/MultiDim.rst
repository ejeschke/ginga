
FITS 파일의 HDU나 3D 큐브 이상 차원의 데이터셋의 평면을 탐색하는 플러그인입니다.

**플러그인 유형: 로컬**

``MultiDim`` 은 로컬 플러그인으로, 채널에 연결되어 있습니다.
각 채널마다 하나의 인스턴스를 열 수 있습니다.

**사용법**

``MultiDim`` 은 데이터 큐브와 다중 HDU FITS 파일을 처리하도록 설계된
플러그인입니다. Ginga에서 그러한 이미지를 열었다면 이 플러그인을 시작하여 큐브의
다른 슬라이스로 이동하거나 다른 HDU를 볼 수 있습니다.

데이터 큐브의 경우 「슬라이스 저장」 버튼을 사용하여 슬라이스를 이미지로
저장하거나, 「시작」과 「끝」 슬라이스 인덱스를 입력하고 「동영상 저장」 버튼을
사용하여 동영상을 만들 수 있습니다. 이 기능을 사용하려면 ``mencoder`` 가 설치되어
있어야 합니다.

FITS 테이블의 경우 데이터는 Astropy 테이블을 사용하여 읽습니다. 열 단위는 메인
헤더 바로 아래에 표시됩니다(단위가 없으면 「None」). 마스크된 열의 경우 마스크된
값은 미리 정의된 채움 값으로 대체됩니다.

**HDU 탐색**

UI 상단의 HDU 드롭다운 목록을 사용하여 채널에서 열 HDU를 탐색하고 선택하십시오.

**큐브 탐색**

UI 하단의 컨트롤을 사용하여 축을 선택하고 해당 축의 평면을 한 단계씩
넘어가십시오.

**사용자 구성**

``~/.ginga/plugin_MultiDim.cfg`` 를 사용하여 사용자 지정할 수 있으며, 여기서
``~`` 는 사용자의 HOME 디렉터리입니다:

.. code-block:: Python

  #
  # MultiDim plugin preferences file
  #
  # Place this in file under ~/.ginga with the name "plugin_MultiDim.cfg"

  # Sort option for HDU listing.
  # Available attributes:
  #   'index' -- Extension index
  #   'name' -- Extension name
  #   'extver' -- Extension version number
  #   'htype' -- HDU type (PrimaryHDU, ImageHDU, TableHDU)
  #   'dtype' -- Data type
  # Example to sort by HDU name and extver:
  #   sort_keys = ['name', 'extver']
  # Default is to sort by index only:
  sort_keys = ['index']

  # Reverse for HDU listing?
  sort_reverse = False
