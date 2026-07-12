``SAMP`` 플러그인은 Ginga 참조 뷰어를 위한 SAMP 인터페이스를 구현합니다.

.. note:: 이 플러그인을 실행하려면 ``samp`` 모듈이 포함된 ``astropy`` 를
          설치해야 합니다.

**플러그인 유형: 전역**

``SAMP`` 는 전역 플러그인입니다. 하나의 인스턴스만 열 수 있습니다.

**사용법**

Ginga에는 SAMP(Simple Applications Messaging Protocol) 지원을 활성화하는
플러그인이 포함되어 있습니다. SAMP 지원을 통해 Ginga는 제어될 수 있으며 다른
천문 데스크톱 응용 프로그램과 상호 운용될 수 있습니다.

``SAMP`` 모듈은 기본적으로 시작되지 않습니다. Ginga가 시작될 때 함께 시작하려면
명령줄 옵션을 지정하십시오::

        --modules=SAMP

그렇지 않으면 「플러그인」 메뉴의 「SAMP 허브 시작」을 사용하여 시작하십시오.

현재 SAMP 지원은 ``image.load.fits`` 메시지로 제한되며, 이는 Ginga가 이러한
메시지 중 하나를 받으면 FITS 파일을 불러온다는 의미입니다.

Ginga의 ``SAMP`` 플러그인은 ``astropy.samp`` 모듈을 사용하므로, 플러그인을
사용하려면 ``astropy`` 가 설치되어 있어야 합니다. 기본적으로 Ginga의 ``SAMP``
플러그인은 실행 중인 SAMP 허브가 없으면 허브 시작을 시도합니다.
