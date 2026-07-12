버퍼 변경 기록을 추적합니다.

**플러그인 유형: 전역**

``ChangeHistory`` 는 전역 플러그인입니다. 하나의 인스턴스만 열 수 있습니다.

이 플러그인은 데이터 버퍼에 대한 모든 변경 사항을 기록하는 데 사용됩니다. 예를
들어 ``Mosaic`` 플러그인을 통해 모자이크에 새 이미지가 추가되면 변경 로그가 여기에
표시됩니다. ``Contents`` 와 마찬가지로 로그는 채널별로, 그다음 이미지 이름별로
정렬됩니다.

**사용법**

기록은 어떤 채널이나 이미지가 활성 상태이든 관계없이 유지되어야 합니다. 새 기록은
추가할 수 있지만, 이미지/채널 자체가 삭제되지 않는 한 오래된 기록은 삭제할 수
없습니다.

``redo()`` 메서드는 ``'add-image-info'`` 이벤트를 받아 관련 메타데이터를 여기에
표시합니다. 메타데이터는 다음과 같이 얻습니다::

        channel = self.fv.get_channel_info(chname)
        iminfo = channel.get_image_info(imname)
        timestamp = iminfo.time_modified
        description = iminfo.reason_modified  # Optional

``'time_modified'`` 와 ``'reason_modified'`` 는 모두 ``'add-image-info'``
콜백을 발생시키는 것과 동일한 메서드에서 호출하는 플러그인이 명시적으로 설정해야
합니다. 다음과 같이::

        # 이것은 데이터 버퍼를 변경합니다
        image.set_data(new_data, ...)
        # ChangeHistory용 설명 추가
        info = dict(time_modified=datetime.now(tz=tz.UTC),
                    reason_modified='Data has changed')
        self.fv.update_image_info(image, info)
