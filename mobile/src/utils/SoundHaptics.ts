import * as Haptics from 'expo-haptics';
import { createAudioPlayer } from 'expo-audio';
import { Platform } from 'react-native';

export const triggerWowEffect = async () => {
  try {
    if (Platform.OS !== 'web') {
      await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    }
    const player = createAudioPlayer(
      { uri: 'https://cdn.pixabay.com/download/audio/2021/08/04/audio_0625c1539c.mp3?filename=success-1-6297.mp3' }
    );
    let disposed = false;
    const dispose = () => {
      if (disposed) return;
      disposed = true;
      clearTimeout(timeout);
      subscription.remove();
      player.remove();
    };
    const subscription = player.addListener('playbackStatusUpdate', status => {
      if (status.didJustFinish) dispose();
    });
    // Release the native player even if the remote sound cannot load.
    const timeout = setTimeout(dispose, 15000);
    try { player.play(); } catch (error) { dispose(); throw error; }
  } catch (error) {
    console.log('Audio/Haptic error ignored', error);
  }
};

export const triggerStealEffect = async () => {
  try {
    if (Platform.OS !== 'web') {
      await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy);
    }
  } catch (error) {}
};
