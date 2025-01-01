from imports import *
intents = discord.Intents.all()
client=discord.Client(intents=intents)
tree= app_commands.CommandTree(client)
voice_client = None
join_channel = None
speakers_file = r"C:\Users\owner\.vscode\voicevox_discord_bot\speaker.json"  # 話者情報を保存するファイル名
default_speaker = 1 
speakers_info_file = r"C:\Users\owner\.vscode\voicevox_discord_bot\speakers_info.json"
# キューを作成して、音声ファイルのパスを管理
audio_queue = []
is_playing = False  # 再生中フラグ
with open("config.json", "r") as f:
    config = json.load(f)

Token = config["DISCORD_TOKEN"]

#commentout.pyに移動(L1~L25)
#現在話者の取得を移動、多分後で実装する

# VOICEVOX API 呼び出し関数
def post_audio_query(text: str, speaker: int):
    URL = "http://127.0.0.1:50021/audio_query"
    Parameters = {"text": text, "speaker": speaker}

    response = requests.post(URL, params=Parameters)
    response.raise_for_status()  # エラーの場合例外を発生
    return response.json()

def post_synthesis(json: dict, speaker: int):
    URL = "http://127.0.0.1:50021/synthesis"
    Parameters = {"speaker": speaker}

    response = requests.post(URL, json=json, params=Parameters)
    response.raise_for_status()  # エラーの場合例外を発生
    return response.content

# 一時ファイルを作成する関数
def save_tempfile(text: str, speaker: int):
    try:
        json = post_audio_query(text, speaker)
        data = post_synthesis(json, speaker)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as wf:
            wf.write(data)
            path = wf.name

        return path
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        return None

@client.event
async def on_ready():
    await client.change_presence(activity=discord.Game(name="頑張って開発してるのだ！"))
    await tree.sync()
    print("ログインしました")
@tree.command(name='test',description='テスト用')
async def test(interaction: discord.Interaction):
    await interaction.response.send_message("テスト成功")

# ボイスチャンネルに接続するコマンド
@tree.command(name="join", description="ボイスチャンネルに接続します。")
async def join(interaction: discord.Interaction):
    global voice_client, join_channel
    user = interaction.user

    if not user.voice:
        await interaction.response.send_message("ボイスチャンネルに接続していません。")
        return

    voice_channel = user.voice.channel
    try:
        if voice_client and voice_client.is_connected():
            await voice_client.disconnect()
            
        voice_client = await voice_channel.connect()
        join_channel = interaction.channel
        await interaction.response.send_message(f"{voice_channel.name} に接続しました。")

        # 音声生成と再生
        path = save_tempfile("接続しました", 1)
        if path:
            print(f"生成された音声ファイルのパス: {path}")
            print("音声ファイルが正常に生成されました。")

            def after_playing(error):
                if error:
                    print(f"再生中のエラー: {error}")
                else:
                    print("音声再生が完了しました。")
                os.remove(path)

            voice_client.play(discord.FFmpegPCMAudio(path, options="-vn"), after=after_playing)

            if not voice_client.is_playing():
                print("音声が再生されていません。")
        else:
            print("音声ファイルの生成に失敗しました。")
            await interaction.response.send_message("音声生成に失敗しました。")
    except Exception as e:
        await interaction.response.send_message(f"エラーが発生しました: {e}")

# ボイスチャンネルから切断するコマンド
@tree.command(name="disconnect", description="ボイスチャンネルから切断します。")
async def disconnect(interaction: discord.Interaction):
    global voice_client

    if not voice_client or not voice_client.is_connected():  # ボイスチャンネルに接続していない場合
        await interaction.response.send_message("ボイスチャンネルに接続していません。")
        return

    try:
        await voice_client.disconnect()
        voice_client = None
        await interaction.response.send_message("切断しました。")
    except Exception as e:
        await interaction.response.send_message(f"エラーが発生しました: {e}")

#commentout.pyに移動(L26~)
#setvoiceコマンドとgetvoiceコマンド

@client.event
async def on_message(message):
    global is_playing  # is_playingをグローバルとして指定
    global voice_client

    # ボット自身のメッセージは無視
    if message.author.bot:
        return

    # 音声生成と再生
    text = f"{message.content}"
    path = save_tempfile(text, 1)  # テキストを音声に変換してファイルに保存

    if path:
        if voice_client and voice_client.is_connected():
            # 既に音声再生中の場合は、音声ファイルをキューに追加
            if not is_playing:
                await play_audio(path, message.channel)
            else:
                audio_queue.append(path)
        else:
            # 音声再生が空いている場合、すぐに再生
            await message.channel.send("ボイスチャンネルに接続中...")
            if not voice_client:
                pass
            await play_audio(path, message.channel)
    else:
        print("音声生成に失敗しました。")

# 音声を再生する関数
async def play_audio(path, channel):
    global is_playing  # is_playingをグローバルとして指定

    # 再生中フラグを立てる
    is_playing = True

    def after_playing(error):
        global is_playing  # is_playingをグローバルとして指定

        if error:
            print(f"再生中のエラー: {error}")
        else:
            print("音声再生が完了しました。")

        os.remove(path)  # 再生後に一時ファイルを削除

        # 再生フラグを解除
        is_playing = False

        # キューに音声があれば次を再生
        if audio_queue:
            next_path = audio_queue.pop(0)  # キューから音声を取り出し再生
            asyncio.run_coroutine_threadsafe(play_audio(next_path, channel), client.loop)

    # 音声再生
    voice_client.play(discord.FFmpegPCMAudio(path, options="-vn"), after=after_playing)


@client.event
async def on_voice_state_update(member, before, after):
    global voice_client, join_channel

    # ボットが参加しているボイスチャンネルの場合のみチェック
    if voice_client and voice_client.is_connected() and member != client.user:
        voice_channel = voice_client.channel

        # チャンネルに誰もいない場合、ボットが自動で切断
        if len(voice_channel.members) == 1 and voice_channel.members[0] == client.user:
            await voice_client.disconnect()

            # ボットが最初に参加したチャンネル（join_channel）にメッセージを送信
            if join_channel:
                await join_channel.send("おつかれさまでした")


client.run(Token)
