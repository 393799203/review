import React from 'react';
import { Switch, Select, Slider, Button, Popover } from 'antd';
import { SettingOutlined, PlayCircleOutlined, SoundOutlined } from '@ant-design/icons';
import { useGlobal } from '../contexts/GlobalContext';

const SpeechSettings = ({ isMobile = false }) => {
  const {
    speechEnabled,
    setSpeechEnabled,
    speechSettings,
    setSpeechSettings,
    availableVoices,
    speechSupported,
    testSpeech,
    getBrowserInfo,
  } = useGlobal();

  if (!speechSupported) {
    return null;
  }

  const settingsContent = (
    <div style={{ width: isMobile ? 250 : 300 }}>
      <div style={{ marginBottom: 16 }}>
        <div style={{ marginBottom: 8, fontWeight: 'bold' }}>语音设置</div>
        <div style={{ marginBottom: 12 }}>
          <div style={{ marginBottom: 4, fontSize: 12, color: '#666' }}>语音包</div>
          <Select
            style={{ width: '100%' }}
            value={speechSettings.voices?.[getBrowserInfo()] || undefined}
            onChange={(value) => {
              const currentBrowser = getBrowserInfo();
              setSpeechSettings({ 
                ...speechSettings, 
                voices: {
                  ...speechSettings.voices,
                  [currentBrowser]: value
                }
              });
            }}
            placeholder="选择语音包"
          >
            {availableVoices.map(voice => (
              <Select.Option key={voice.name} value={voice.name}>
                {voice.name} ({voice.lang})
              </Select.Option>
            ))}
          </Select>
        </div>
        <div style={{ marginBottom: 12 }}>
          <div style={{ marginBottom: 4, fontSize: 12, color: '#666' }}>语速: {speechSettings.rate.toFixed(1)}</div>
          <Slider
            min={0.5}
            max={2}
            step={0.1}
            value={speechSettings.rate}
            onChange={(value) => setSpeechSettings({ ...speechSettings, rate: value })}
          />
        </div>
        <div style={{ marginBottom: 12 }}>
          <div style={{ marginBottom: 4, fontSize: 12, color: '#666' }}>音调: {speechSettings.pitch.toFixed(1)}</div>
          <Slider
            min={0.5}
            max={2}
            step={0.1}
            value={speechSettings.pitch}
            onChange={(value) => setSpeechSettings({ ...speechSettings, pitch: value })}
          />
        </div>
        <div style={{ marginBottom: 12 }}>
          <div style={{ marginBottom: 4, fontSize: 12, color: '#666' }}>音量: {speechSettings.volume.toFixed(1)}</div>
          <Slider
            min={0}
            max={1}
            step={0.1}
            value={speechSettings.volume}
            onChange={(value) => setSpeechSettings({ ...speechSettings, volume: value })}
          />
        </div>
        <Button
          type="primary"
          size="small"
          icon={<PlayCircleOutlined />}
          onClick={testSpeech}
          block
        >
          试听效果
        </Button>
      </div>
    </div>
  );

  if (isMobile) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
        <SoundOutlined style={{ fontSize: 14, color: '#666' }} />
        <Switch
          checked={speechEnabled}
          onChange={setSpeechEnabled}
          size="small"
        />
        <Popover
          content={settingsContent}
          title={null}
          trigger="click"
          placement="bottomRight"
        >
          <Button
            type="text"
            icon={<SettingOutlined />}
            size="small"
            style={{ color: '#1890ff', padding: '0 4px' }}
          />
        </Popover>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <span style={{ fontSize: 14, color: '#666' }}>播报</span>
      <Switch
        checked={speechEnabled}
        onChange={setSpeechEnabled}
        size="small"
      />
      <Popover
        content={settingsContent}
        title={null}
        trigger="click"
        placement="bottomRight"
      >
        <Button
          type="text"
          icon={<SettingOutlined />}
          size="small"
          style={{ color: '#1890ff' }}
        />
      </Popover>
    </div>
  );
};

export default SpeechSettings;
