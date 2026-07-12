
``RC`` 플러그인은 Ginga 뷰어를 위한 원격 제어 인터페이스를 구현합니다.

**플러그인 유형: 전역**

``RC`` 는 전역 플러그인입니다. 하나의 인스턴스만 열 수 있습니다.

**사용법**

``RC``(Remote Control) 플러그인은 XML-RPC 인터페이스를 사용하여 Ginga를 원격으로
제어하는 방법을 제공합니다. 「Plugins」 메뉴에서 플러그인을 시작하거나(「Start
RC」 호출) ``--modules=RC`` 명령줄 옵션으로 ginga를 실행하여 자동으로
시작하십시오.

기본적으로 플러그인은 localhost 인터페이스에 바인딩된 포트 11771에서 실행되는
서버로 시작됩니다 -- 이는 로컬 호스트에서의 연결만 허용합니다. 이를 변경하려면
「Set Addr」 컨트롤에서 호스트와 포트를 설정하고 ``Enter`` 를 누르십시오 --
「Addr:」 표시 필드에서 주소가 업데이트되는 것을 볼 수 있습니다.

호스트 부분(콜론 앞)은 *어느* 호스트로부터의 접근을 허용할지를 나타내는 것이
아니라 어떤 인터페이스에 바인딩할지를 나타낸다는 점에 유의하십시오. 모든 호스트의
연결을 허용하려면 비워 두어(단, 콜론과 포트 번호는 포함) 서버가 모든 인터페이스에
바인딩되도록 하십시오. 그런 다음 「Restart」를 눌러 새 주소에서 서버를 다시
시작하십시오.

플러그인이 시작되면 ``ggrc`` 스크립트(``ginga`` 설치 시 포함됨)를 사용하여 Ginga를
제어할 수 있습니다. 자신만의 프로그래밍 인터페이스를 작성하는 방법을 보려면 이
스크립트를 살펴보십시오.

사용 예 표시::

        $ ggrc help

특정 Ginga 메서드에 대한 도움말 표시::

        $ ggrc help ginga <method>

특정 채널 메서드에 대한 도움말 표시::

        $ ggrc help channel <chname> <method>

Ginga(뷰어 셸) 메서드는 다음과 같이 호출할 수 있습니다::

        $ ggrc ginga <method> <arg1> <arg2> ...

채널별 메서드는 다음과 같이 호출할 수 있습니다::

        $ ggrc channel <chname> <method> <arg1> <arg2> ...

옵션을 추가하여 원격 호스트에서 호출할 수 있습니다::

        --host=<hostname> --port=11771

(플러그인 GUI에서 「addr」에서 「localhost」 접두사를 반드시 제거하되, 콜론과
포트는 남겨 두십시오.)

**예제**

새 채널 만들기::

        $ ggrc ginga add_channel FOO

파일 불러오기::

        $ ggrc ginga load_file /home/eric/testdata/SPCAM/SUPA01118797.fits

특정 채널에 파일 불러오기::

        $ ggrc ginga load_file /home/eric/testdata/SPCAM/SUPA01118797.fits FOO

컷 레벨::

        $ ggrc channel FOO cut_levels 163 1300

자동 컷 레벨::

        $ ggrc channel FOO auto_levels

특정 레벨로 확대::

        $ ggrc -- channel FOO zoom_to -7

(``-`` 로 시작하는 매개변수를 전달할 수 있도록 하기 위한 ``--`` 의 사용에
유의하십시오.)

맞춤 확대::

        $ ggrc channel FOO zoom_fit

변환(인수는 불리언 세 쌍: ``flipx`` ``flipy`` ``swapxy``)::

        $ ggrc channel FOO transform 1 0 1

회전::

        $ ggrc channel FOO rotate 37.5

색상 맵 변경::

        $ ggrc channel FOO set_color_map rainbow3

색상 분포 알고리즘 변경::

        $ ggrc channel FOO set_color_algorithm log

강도 맵 변경::

        $ ggrc channel FOO set_intensity_map neg

경우에 따라 특정 문자를 Ginga에 전달할 수 있도록 셸 이스케이프에 의존해야 할 수도
있습니다. 예를 들어, 앞에 오는 대시 문자는 보통 프로그램 옵션으로 해석됩니다.
부호 있는 정수를 전달하려면 다음과 같이 해야 할 수도 있습니다::

        $ ggrc -- channel FOO zoom -7

**Python 내에서 인터페이스하기**

Python 내에서 RC 모드로 Ginga를 제어하는 것도 가능합니다. 다음은 기능의 일부를
설명합니다.

*연결하기*

먼저 Ginga를 실행하고 ``RC`` 플러그인을 시작하십시오. 이것은 명령줄에서 할 수
있습니다::

        ginga --modules=RC

Python 내에서 다음과 같이 ``RemoteClient`` 객체로 연결하십시오::

        from ginga.util import grc
        host = 'localhost'
        port = grc.default_rc_port
        viewer = grc.RemoteClient(host, port)

이 viewer 객체는 이제 ``RC`` 를 사용하여 Ginga에 연결되어 있습니다.

*이미지 불러오기*

원하는 채널에 메모리에서 이미지를 불러올 수 있습니다. 먼저 채널에 연결하십시오::

        ch = viewer.channel('Image')

그런 다음 Numpy 이미지(즉, 임의의 2D ``ndarray``)를 불러오십시오::

        import numpy as np
        img = np.random.rand(500, 500) * 10000.0
        ch.load_np('Image_Name', img, 'fits', {})

이미지는 Ginga에 표시되고 평소처럼 조작할 수 있습니다.

*캔버스 객체 겹치기*

특정 채널의 캔버스에 객체를 추가할 수 있습니다. 먼저 연결하십시오::

        canvas = viewer.canvas('Image')

이것은 「Image」라는 채널에 연결합니다. 캔버스에 그려진 객체를 지울 수 있습니다::

        canvas.clear()

임의의 기본 캔버스 객체를 추가할 수도 있습니다. 명심해야 할 핵심 사항은 입력하는
객체가 XMLRC 프로토콜을 통과해야 한다는 것입니다. 이는 단순한 데이터 유형(``float``,
``int``, ``list`` 또는 ``str``)을 의미합니다. 배열은 안 됩니다. 다음은 두 개의
Numpy 배열로 정의된 일련의 점을 통과하는 선을 플롯하는 예입니다::

        x = np.arange(100)
        y = np.sqrt(x)
        points = list(zip(x.tolist(), y.tolist()))
        canvas.add('path', points, color='red')

이것은 이미지에 빨간색 선을 그립니다.
