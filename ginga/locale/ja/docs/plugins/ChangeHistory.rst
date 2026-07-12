バッファの変更履歴を記録します。

**プラグインの種類: グローバル**

``ChangeHistory`` はグローバルプラグインです。開けるインスタンスは 1 つだけです。

このプラグインは、データバッファへのあらゆる変更を記録するために使います。例えば
``Mosaic`` プラグインでモザイクに新しい画像が追加されると、変更ログがここに表示
されます。``Contents`` と同様に、ログはチャンネル順、次に画像名順に並べられます。

**使い方**

履歴は、どのチャンネルや画像がアクティブであっても残ります。新しい履歴は追加でき
ますが、古い履歴は、画像／チャンネル自体を削除しない限り削除できません。

``redo()`` メソッドは ``'add-image-info'`` イベントを受け取り、関連するメタデータ
をここに表示します。メタデータは次のように取得します::

        channel = self.fv.get_channel_info(chname)
        iminfo = channel.get_image_info(imname)
        timestamp = iminfo.time_modified
        description = iminfo.reason_modified  # Optional

``'time_modified'`` と ``'reason_modified'`` の両方は、``'add-image-info'``
コールバックを発行するのと同じメソッド内で、呼び出し側のプラグインが明示的に設定
する必要があります。次のように::

        # これはデータバッファを変更する
        image.set_data(new_data, ...)
        # ChangeHistory 用の説明を追加
        info = dict(time_modified=datetime.now(tz=tz.UTC),
                    reason_modified='Data has changed')
        self.fv.update_image_info(image, info)
