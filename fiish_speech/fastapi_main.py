import io
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
# from fastapi_standalone_docs import StandaloneDocs
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from tools.server.inference import inference_wrapper as inference
from tools.server.model_manager import ModelManager
from fish_speech.utils.schema import ServeReferenceAudio, ServeTTSRequest
from fish_speech.utils.file import audio_to_bytes, read_ref_text
import soundfile as sf

# 初始化 FastAPI 应用
app = FastAPI()

# StandaloneDocs(app=app)
# 添加 CORS 中间件（根据需要调整）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 根据需要限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



class TTSRequest(BaseModel):
    text: str
    streaming: bool = False
# 定义请求模型
@app.post("/tts/")
async def tts(req_test: TTSRequest, streaming: bool = False, character: str = "wx"):
    # Perform TTS
    engine = model_manager.tts_inference_engine
    if character == "wx":
        ref_texts = ["路基智能设计子系统：以数据为核心，模型为承载，实现了支挡结构、排水工程、边坡防护、基床填挖方及地基处理的参数化设计和模型联动更新。软件已成功应用于长沙至浏阳市域(郊)铁路、台州市域S2线，深汕铁路的BIM建模项目。相比于Revit、Bently的传统方法，本系统提高了路基三维设计效率约10倍以上。"]
        ref_audios = ["data/wx.wav"]
    if character == "dz":
        ref_texts = ["阿爸阿妈已经把中午饭准备好了。",
                    "讲我和动物朋友们的故事。",
                    "在山里我能听到各种各样的叫声。",
                    "这是礼堂的环保。",
                    "这是猞猁。"
                    ]
        ref_audios = ["data/阿爸阿妈已经把中午饭准备好了。.mp3",
                    "data/讲我和动物朋友们的故事。.mp3",
                    "data/在山里我能听到各种各样的叫声。.mp3",
                    "data/这是礼堂的环保。.mp3",
                    "data/这是猞猁。.mp3"
                    ]

    byte_audios = [audio_to_bytes(ref_audio) for ref_audio in ref_audios]
    # print(byte_audios)
    references = [
            ServeReferenceAudio(
                audio=ref_audio if ref_audio is not None else b"", text=ref_text
            )
            for ref_text, ref_audio in zip(ref_texts, byte_audios)
        ]
    # print(references)

    req = ServeTTSRequest(
        text=req_test.text,
        chunk_length= 200,
        format="wav",
        references=references,
        reference_id = None,
        seed=None,
        use_memory_cache="on",
        normalize=True,
        streaming=req_test.streaming,
        max_new_tokens=1024,
        top_p=0.7,
        repetition_penalty=1.2,
        temperature=0.7
    )

    fake_audios = next(inference(req, engine))
    buffer = io.BytesIO()
    sf.write(
        buffer,
        fake_audios,
        engine.decoder_model.spec_transform.sample_rate,
        format=req.format,
    )

    # 设置文件指针的位置为文件的开始，确保响应时能够从头开始读取
    buffer.seek(0)

    # 保存生成的音频文件
    with open(f"audio.{req.format}", "wb") as f:
        f.write(buffer.getvalue())

    # 返回生成的音频文件
    return StreamingResponse(buffer, media_type="audio/wav")

    # return StreamResponse(
    #     iterable=buffer_to_async_generator(buffer.getvalue()),
    #     headers={
    #         "Content-Disposition": f"attachment; filename=audio.{req.format}",
    #     },
    #     content_type=get_content_type(req.format),
    # )

if __name__ == "__main__":
    model_manager = ModelManager(
            mode="tts",
            device="cuda",
            half=False,
            compile=True,
            asr_enabled=False,
            llama_checkpoint_path="checkpoints/fish-speech-1.5",
            decoder_checkpoint_path="checkpoints/fish-speech-1.5/firefly-gan-vq-fsq-8x1024-21hz-generator.pth",
            decoder_config_name="firefly_gan_vq",
        )
    uvicorn.run(app, host="0.0.0.0", port=7860)