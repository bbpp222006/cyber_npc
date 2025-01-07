import { VRMExpressionPresetName } from "@pixiv/three-vrm";
import { LipSyncAnalyzeResult } from "./lipSyncAnalyzeResult";

const TIME_DOMAIN_DATA_LENGTH = 2048;

export class LipSync {
  public readonly audio: AudioContext;
  public readonly analyser: AnalyserNode;
  public readonly timeDomainData: Float32Array;
  public readonly frequencyData: Float32Array;

  public constructor(audio: AudioContext) {
    this.audio = audio;

    this.analyser = audio.createAnalyser();
    this.timeDomainData = new Float32Array(TIME_DOMAIN_DATA_LENGTH);
    this.frequencyData = new Float32Array(TIME_DOMAIN_DATA_LENGTH);
  }

  public update(): LipSyncAnalyzeResult {
    this.analyser.getFloatTimeDomainData(this.timeDomainData);

    let volume = 0.0;
    for (let i = 0; i < TIME_DOMAIN_DATA_LENGTH; i++) {
      volume = Math.max(volume, Math.abs(this.timeDomainData[i]));
    }

    // cook
    volume = 1 / (1 + Math.exp(-45 * volume + 5));
    if (volume < 0.1) volume = 0;

    // 3. 获取频域数据（FFT 结果）-----------------------------------------
    this.analyser.getFloatFrequencyData(this.frequencyData);

    // 4. 基于频谱来推断当前发音
    const phoneme = this.analyzePhoneme(this.frequencyData);

    return {
      volume,
      phoneme,
    };
  }

  private analyzePhoneme(frequencyData: Float32Array): VRMExpressionPresetName {
    // 1. 准备划分的频带区间（单位：Hz），以及频率 bin 与 Hz 的转换
    //    通常 sampleRate = 44100 或 48000，根据具体音频上下文而定
    const sampleRate = 44100;
    const fftSize = this.analyser.fftSize; // e.g. 1024 / 2048
    const binSize = sampleRate / fftSize;  // 每个 bin 对应多少 Hz

    // 2. 定义一些频带区间 (只是演示，可自行调整)
    const lowFreqRange = [100, 400];   // 低频
    const midFreqRange = [400, 1600];  // 中频
    const highFreqRange = [1600, 5000]; // 高频

    // 3. 计算各频带的总能量 (分贝值为负，但越大表示能量越强)
    const lowEnergy = this.getBandEnergy(frequencyData, lowFreqRange, binSize);
    const midEnergy = this.getBandEnergy(frequencyData, midFreqRange, binSize);
    const highEnergy = this.getBandEnergy(frequencyData, highFreqRange, binSize);

    // 4. 做一个简单的比较，选出最大频带 + 结合一些经验逻辑映射到元音
    //    这里仅是示例，实际可以更细分或使用多段判断
    let maxBand = "low";
    let maxValue = lowEnergy;

    if (midEnergy > maxValue) {
      maxBand = "mid";
      maxValue = midEnergy;
    }
    if (highEnergy > maxValue) {
      maxBand = "high";
      maxValue = highEnergy;
    }

    // 5. 根据“最大频带”和几个区间对比来猜测当前发音
    //    下面是非常“拍脑袋”的规则示例，需要配合实际测试微调
    if (maxBand === "low" && midEnergy > (lowEnergy - 5)) {
      // 低频和中频都比较突出 => "oh" 或 "aa"
      return "aa";
    } else if (maxBand === "low") {
      return "ou";
    } else if (maxBand === "mid") {
      // mid 最突出 => "ih" 或 "oh"
      return "oh";
    } else if (maxBand === "high") {
      // high 最突出 => "ee" 或 "ih"
      return "ee";
    }

    // 兜底返回 Neutral
    return "ou";
  }

  private getBandEnergy(
    frequencyData: Float32Array,
    [minFreq, maxFreq]: number[],
    binSize: number
  ): number {
    let sum = 0;
    let count = 0;
  
    const startBin = Math.floor(minFreq / binSize);
    const endBin = Math.floor(maxFreq / binSize);
  
    // frequencyData[i] 是分贝值（负数越大代表能量越强）
    // 可以将其转为“幅度”再做平均，也可直接在分贝域中取平均。
    // 这里直接使用分贝值做平均。
    for (let i = startBin; i <= endBin && i < frequencyData.length; i++) {
      sum += frequencyData[i];
      count++;
    }
    return count > 0 ? sum / count : -Infinity;
  }

  public async playFromArrayBuffer(buffer: ArrayBuffer, onEnded?: () => void) {
    const audioBuffer = await this.audio.decodeAudioData(buffer);

    const bufferSource = this.audio.createBufferSource();
    bufferSource.buffer = audioBuffer;

    bufferSource.connect(this.audio.destination);
    bufferSource.connect(this.analyser);
    bufferSource.start();
    if (onEnded) {
      bufferSource.addEventListener("ended", onEnded);
    }
  }

  public async playFromURL(url: string, onEnded?: () => void) {
    const res = await fetch(url);
    const buffer = await res.arrayBuffer();
    this.playFromArrayBuffer(buffer, onEnded);
  }
}
