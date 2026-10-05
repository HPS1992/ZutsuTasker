// Temporary dummy file to prevent expo-notifications from crashing the app
export async function registerForPushNotificationsAsync() {
  console.log("Push notifications temporarily disabled for release testing.");
  return null;
}
