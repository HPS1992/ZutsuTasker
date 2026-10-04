import { Expo } from 'expo-server-sdk';
import { PrismaClient } from '@prisma/client';

const expo = new Expo();
const prisma = new PrismaClient();

export const notificationService = {
  async notifyGroup(groupId: string, title: string, body: string, excludeUserId?: string) {
    const members = await prisma.groupMember.findMany({
      where: { group_id: groupId },
      include: { user: true }
    });

    const messages: any[] = [];
    for (const member of members) {
      if (member.user_id === excludeUserId) continue;
      
      const pushToken = member.user.push_token;
      if (pushToken && Expo.isExpoPushToken(pushToken)) {
        messages.push({
          to: pushToken,
          sound: 'default',
          title,
          body,
          data: { groupId },
        });
      }
    }

    const chunks = expo.chunkPushNotifications(messages);
    for (const chunk of chunks) {
      try {
        await expo.sendPushNotificationsAsync(chunk);
      } catch (error) {
        console.error('Error enviando push notifications', error);
      }
    }
  }
};
