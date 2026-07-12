간단한 천문 항성 분석을 수행합니다.

**플러그인 유형: 로컬**

``Pick`` 은 로컬 플러그인으로, 채널에 연결되어 있습니다.
싱글턴이 아니므로 각 채널마다 여러 인스턴스를 열 수 있습니다.

**사용법**

``Pick`` 플러그인은 항성 객체에 대해 간단한 천문 데이터 품질 분석을 수행하는 데
사용됩니다. 그린 상자 안에서 항성 후보를 찾아 일련의 검색 설정에 기반하여 가장
가능성 높은 후보를 선택합니다. 후보 객체에 대한 반치전폭(FWHM)이 보고되며,
검출기의 플레이트 스케일에 기반한 크기도 보고됩니다. 배경, 하늘 레벨 및 밝기의
대략적인 측정도 수행됩니다.

**Pick 영역 정의**

기본 Pick 영역은 검색 영역을 둘러싸는 약 30x30 픽셀의 상자로 정의됩니다.

플러그인 하단의 이동/그리기/편집 선택기는 Pick 영역에 대해 어떤 작업을 수행하는지
결정하는 데 사용됩니다:

.. figure:: figures/pick-move-draw-edit.png
   :width: 400px
   :align: center
   :alt: 이동, 그리기, 편집 버튼

   「이동」, 「그리기」, 「편집」 버튼.

* 「이동」이 선택되면 기존 Pick 영역을 끌어서 이동하거나 중심을 두고 싶은 곳을
  클릭할 수 있습니다. 기존 영역이 없으면 기본 영역이 생성됩니다.
* 「그리기」가 선택되면 커서로 도형을 그려 새 Pick 영역을 둘러싸고 정의할 수
  있습니다. 기본 도형은 상자이지만 「Settings」 탭에서 다른 도형을 선택할 수
  있습니다.
* 「편집」이 선택되면 제어점을 끌어 Pick 영역을 편집하거나 경계 상자 안에서 끌어
  이동할 수 있습니다.

영역을 이동, 그리기 또는 편집한 후 ``Pick`` 은 영역에서 모든 피크를 검색하고 UI의
「Settings」 탭의 기준(아래 「Settings 탭」 참조)에 기반하여 피크를 평가한 다음
설정에 가장 잘 맞는 최적의 후보를 찾으려고 시도합니다.

.. note:: 「Quick Mode」와 「From Peak」 체크박스는 Ginga 릴리스 v4.0에서
          제거되었습니다.

**후보가 발견된 경우**

후보는 수평 및 수직 FWHM 측정으로 결정된 객체를 중심으로 채널 뷰어 캔버스에
점(보통 「X」)으로 표시됩니다.

UI 상단의 탭 세트는 다음과 같이 채워집니다:

.. figure:: figures/pick-cutout.png
   :width: 400px
   :align: center
   :alt: Pick 영역의 Image 탭

   ``Pick`` 영역의 「Image」 탭.

「Image」 탭은 잘라낸 영역의 내용을 표시합니다. 이 탭의 위젯은 Ginga 위젯이므로
일반적인 키보드 및 마우스 바인딩(예: 스크롤 휠)으로 확대/축소하고 팬할 수 있습니다.
객체를 중심으로 한 점으로도 표시되며, 추가로 팬 위치가 발견된 중심으로 설정됩니다.

.. figure:: figures/pick-contour.png
   :width: 300px
   :align: center
   :alt: Pick 영역의 Contour 탭

   ``Pick`` 영역의 「Contour」 탭.

「Contour」 탭은 등고선 플롯을 표시합니다. 이것은 후보 바로 주변 영역의 등고선
플롯이며, 보통 Pick 영역의 전체를 포함하지는 않습니다. 스크롤 휠을 사용하여 플롯을
확대할 수 있고, 스크롤 휠 클릭(마우스 버튼 2)으로 플롯의 팬 위치를 설정할 수
있습니다.

.. figure:: figures/pick-fwhm.png
   :width: 400px
   :align: center
   :alt: Pick 영역의 FWHM 탭

   ``Pick`` 영역의 「FWHM」 탭.

「FWHM」 탭은 FWHM 플롯을 표시합니다. 보라색 선은 X 방향의 측정을, 녹색 선은 Y
방향의 측정을 나타냅니다. 실선은 실제 픽셀 값을, 점선은 맞춘 1D 함수를 나타냅니다.
음영 처리된 보라색과 녹색 영역은 각 축의 FWHM 측정을 나타냅니다.

.. figure:: figures/pick-radial.png
   :width: 400px
   :align: center
   :alt: Pick 영역의 Radial 탭

   ``Pick`` 영역의 「Radial」 탭.

「Radial」 탭에는 동경 프로파일 플롯이 있습니다. 보라색으로 플롯된 점은 데이터
값이며, 데이터에 선이 맞춰집니다.

.. figure:: figures/pick-ee.png
   :width: 600px
   :align: center
   :alt: Pick 영역의 EE 탭

   ``Pick`` 영역의 「EE」 탭.

「EE」 탭에는 선택한 대상에 대해 각각 보라색과 녹색으로 된 분수 원 내(encircled)
및 사각 내(ensquared) 에너지(EE) 플롯이 있습니다. EE 값을 측정하기 전에 FWHM 계산과
일관된 방식으로 간단한 배경 빼기가 수행됩니다. 검은색 파선으로 표시된 샘플링 반경과
전체 반경은 「Settings」 탭에서 설정할 수 있으며, 이들을 변경하면 「Redo Pick」을
클릭하여 플롯과 측정을 업데이트하십시오. 주어진 샘플링 반경에서 측정된 EE 값은
「Readout」 탭에도 표시됩니다. 보고가 요청되면 주어진 샘플링 반경에서의 EE 값과 반경
자체가 다른 정보와 함께 「Report」 표에 기록됩니다.

「Show Candidates」가 활성 상태이면 경계 상자 가장자리 근처의 후보는 EE 값을 갖지
않습니다(0으로 설정).

.. figure:: figures/pick-readout.png
   :width: 400px
   :align: center
   :alt: Pick 영역의 Readout 탭

   ``Pick`` 영역의 「Readout」 탭.

「Readout」 탭은 측정 요약으로 채워집니다. 이 탭에는 두 개의 버튼과 세 개의
체크박스가 있습니다:

* 「Default Region」 버튼은 Pick 영역을 기본 도형과 크기로 복원합니다.
* 「Pan to pick」 버튼은 채널 뷰어를 찾은 중심으로 팬합니다.
* 「Center on pick」이 선택되어 있으면 도형이 찾은 중심으로 재중심화됩니다(찾은
  경우. 즉, 도형이 Pick을 「추적」합니다).

.. figure:: figures/pick-controls.png
   :width: 400px
   :align: center
   :alt: Pick 영역의 Controls 탭

   ``Pick`` 영역의 「Controls」 탭.

「Controls」 탭에는 측정을 바탕으로 작동하는 몇 개의 버튼이 있습니다.

* 「Bg cut」 버튼은 채널 뷰어의 낮은 컷 레벨을 측정된 배경 레벨로 설정합니다. 이
  값에 대한 델타는 「Delta bg」 상자에 값을 설정하여 적용할 수 있습니다(설정을
  변경하려면 「Enter」를 누르십시오).
* 「Sky cut」 버튼은 채널 뷰어의 낮은 컷 레벨을 측정된 하늘 레벨로 설정합니다. 이
  값에 대한 델타는 「Delta sky」 상자에 값을 설정하여 적용할 수 있습니다(설정을
  변경하려면 「Enter」를 누르십시오).
* 「Bright cut」 버튼은 채널 뷰어의 높은 컷 레벨을 측정된 하늘+밝기 레벨로
  설정합니다. 이 값에 대한 델타는 「Delta bright」 상자에 값을 설정하여 적용할 수
  있습니다(설정을 변경하려면 「Enter」를 누르십시오).

.. figure:: figures/pick-report.png
   :width: 400px
   :align: center
   :alt: Pick 영역의 Report 탭

   ``Pick`` 영역의 「Report」 탭.

「Report」 탭은 측정에 대한 정보를 표 형식으로 기록하는 데 사용됩니다.

「Add Pick」 버튼을 누르면 가장 최근 후보에 대한 정보가 표에 추가됩니다. 「Record
Picks automatically」 체크박스가 선택되어 있으면 어떤 후보든 자동으로 표에
추가됩니다.

.. note:: 「Settings」 탭의 「Show Candidates」 체크박스가 선택되어 있으면 선택된
          후보만이 아니라 (설정에 따라) 영역에서 발견된 *모든* 객체가 표에
          추가됩니다.

「Clear Log」 버튼을 눌러 언제든지 표를 지울 수 있습니다. 로그는 「File:」 상자에
유효한 경로와 파일 이름을 넣고 「Save table」을 눌러 표에 저장할 수 있습니다. 파일
유형은 주어진 확장자에 의해 자동으로 결정됩니다(예: 「.fits」는 FITS, 「.txt」는
일반 텍스트).

**후보가 발견되지 않은 경우**

(설정에 기반하여) 후보를 찾을 수 없으면 Pick 영역이 Pick 영역을 중심으로 한 빨간
점으로 표시됩니다.

.. figure:: figures/pick-no-candidate.png
   :width: 800px
   :align: center
   :alt: 후보가 발견되지 않았을 때의 마커

   후보가 발견되지 않았을 때의 마커.

이미지 잘라내기는 이 중앙 영역에서 취해지므로 「Image」 탭에는 여전히 내용이
있습니다. 중앙의 빨간 「X」로도 표시됩니다.

등고선 플롯은 여전히 잘라내기에서 생성됩니다.

.. figure:: figures/pick-contour-no-candidate.png
   :width: 400px
   :align: center
   :alt: 후보가 발견되지 않았을 때의 등고선.

   후보가 발견되지 않았을 때의 등고선.

다른 모든 플롯은 지워집니다.

**Settings 탭**

.. figure:: figures/pick-settings.png
   :width: 400px
   :align: center
   :alt: Pick 플러그인의 Settings 탭

   ``Pick`` 플러그인의 「Settings」 탭.

「Settings」 탭은 Pick 영역 내 검색의 여러 측면을 제어합니다:

* 「Show Candidates」 체크박스는 검출된 모든 소스를 표시할지 여부를 제어합니다(아래
  그림 참조). 또한 선택되어 있으면 「Report」 컨트롤을 사용할 때 발견된 모든 객체가
  Pick 로그 표에 추가됩니다.
* 「Draw type」 매개변수는 그릴 Pick 영역의 도형을 선택하는 데 사용됩니다.
* 「Radius」 매개변수는 이미지에서 밝은 피크를 찾고 평가할 때 사용할 반경을
  설정합니다.
* 「Threshold」 매개변수는 피크 찾기의 임계값을 설정하는 데 사용됩니다. 「None」으로
  설정하면 합리적인 기본값이 선택됩니다.
* 「Min FWHM」과 「Max FWHM」 매개변수는 특정 크기의 객체를 후보에서 제외하는 데
  사용할 수 있습니다.
* 「Ellipticity」 매개변수는 도형의 비대칭성에 기반하여 후보를 제외하는 데
  사용됩니다.
* 「Edge」 매개변수는 잘라내기 가장자리에 얼마나 가까운지에 기반하여 후보를 제외하는
  데 사용됩니다. *참고: 현재 이것은 회전되지 않은 직사각형 도형에 대해서만 안정적
  으로 작동합니다.*
* 「Max side」 매개변수는 Pick 도형에 사용할 수 있는 경계 상자의 크기를 제한하는 데
  사용됩니다. 크기가 클수록 평가에 시간이 더 오래 걸립니다.
* 「Coordinate Base」 매개변수는 찾은 소스에 적용할 오프셋입니다. 소스 픽셀 위치를
  FITS 호환 방식으로 보고하려면 「1」로, 0 기반 인덱싱을 선호하면 「0」으로
  설정하십시오.
* 「Calc center」 매개변수는 중심을 FWHM 맞춤(「fwhm」)에서 계산할지 무게중심화
  (「centroid」)에서 계산할지 결정하는 데 사용됩니다.
* 「FWHM fitting」 매개변수는 FWHM 맞춤에 어떤 함수를 사용할지(「gaussian」 또는
  「moffat」) 결정하는 데 사용됩니다. ``~/.ginga/plugin_Pick.cfg`` 에서
  「calc_fwhm_lib」가 「astropy」로 설정되어 있으면 「lorentz」를 사용하는 옵션도
  사용할 수 있습니다.
* 「Contour Interpolation」 매개변수는 「Contour」 플롯에서 배경 이미지를 렌더링할
  때 사용하는 보간 방법을 설정하는 데 사용됩니다.
* 「EE total radius」는 EE 분수가 1이 될 것으로 예상되는(즉, 점 확산 함수의 모든
  플럭스가 안에 포함되는) 반경(원 내 에너지용)과 상자 반너비(사각 내 에너지용)를
  픽셀로 정의합니다.
* 「EE sampling radius」는 보고를 위해 측정된 EE 곡선을 샘플링하는 데 사용하는
  반경(픽셀)입니다.

「Redo Pick」 버튼은 검색 작업을 다시 수행합니다. 일부 매개변수를 변경하고 현재
Pick 영역을 방해하지 않으면서 그 효과를 보고 싶을 때 편리합니다.

.. figure:: figures/pick-candidates.png
   :width: 600px
   :align: center
   :alt: 「Show Candidates」가 선택되어 있을 때의 채널 뷰어.

   「Show Candidates」가 선택되어 있을 때의 채널 뷰어.

**사용자 구성**

``~/.ginga/plugin_Pick.cfg`` 를 사용하여 사용자 지정할 수 있으며, 여기서 ``~`` 는
사용자의 HOME 디렉터리입니다:

.. code-block:: Python

  #
  # Pick plugin preferences file
  #
  # Place this in file under ~/.ginga with the name "plugin_Pick.cfg"

  color_pick = 'green'
  shape_pick = 'box'
  color_candidate = 'purple'

  # Offset to add to Pick results. Default is 1.0 for FITS like indexing,
  # set to 0.0 here if you prefer numpy-like 0-based indexing
  pixel_coords_offset = 0.0

  # Maximum side for a pick region
  max_side = 1024

  # For image cutout viewer ("Image" tab)
  # you can set autozoom and autocuts preferences
  cutout_autozoom = 'override'
  cutout_autocuts = 'off'

  # For contour plot ("Contour" tab)
  # widget type: let choose automatically or force 'ginga' or 'matplotlib'
  # (choice of 'ginga' requires scikit-image to be installed)
  contour_widget = 'choose'
  # if ginga widget is chosen, you can set autozoom and autocuts preferences
  contour_autozoom = 'override'
  contour_autocuts = 'override'
  num_contours = 8
  # How big of a radius are we willing to consider from the center of the
  # pick?  bigger numbers == slower
  contour_size_min = 10
  contour_size_limit = 70

  # should the pick shape recenter on the found object center, if any?
  # useful for "tracking" an object that is moving from image to image
  center_on_pick = False

  # Star candidate search parameters
  radius = 10
  # Set threshold to None to auto calculate it
  threshold = None
  # Minimum and maximum fwhm to be considered a candidate
  min_fwhm = 1.5
  max_fwhm = 50.0
  # Minimum ellipticity to be considered a candidate
  min_ellipse = 0.5
  # Percentage from edge to be considered a candidate
  edge_width = 0.01
  # Graphically indicate all possible considered candidates
  show_candidates = False

  # Center of object is based on FWHM ("fwhm") or centroid ("centroid")
  # calculation:
  calc_center_alg = 'centroid'

  # Library to use for FWHM fitting ("native" or "astropy")
  calc_fwhm_lib = 'native'

  # Fitting function to use for FWHM ("gaussian" or "moffat")
  calc_fwhm_alg = 'gaussian'

  # Defaults for delta cut levels (in Controls tab)
  delta_sky = 0.0
  delta_bright = 0.0

  # Encircled and ensquared energy (EE) calculations:
  # a. Radius (pixel) where EE fraction is expected to be 1.
  ee_total_radius = 10.0
  # b. Radius (pixel) to sample EE for reporting.
  ee_sampling_radius = 2.5

  # use a different color/intensity map than channel image?
  pick_cmap_name = None
  pick_imap_name = None

  # For Reports tab
  record_picks = True

  # Set this to a file name, if None a filename will be automatically chosen
  report_log_path = None
