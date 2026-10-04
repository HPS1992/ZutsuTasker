import * as Haptics from 'expo-haptics';
import { Audio } from 'expo-av';
import { Platform } from 'react-native';

export const triggerWowEffect = async () => {
  try {
    if (Platform.OS !== 'web') {
      await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    }
    const { sound } = await Audio.Sound.createAsync(
      { uri: 'https://cdn.pixabay.com/download/audio/2021/08/04/audio_0625c1539c.mp3?filename=success-1-6297.mp3' }
    );
    await sound.playAsync();
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
