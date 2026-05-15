import preferences from '@ohos.data.preferences';

export class PreferenceUtil {
  private static context: Context;

  static init(context: Context) {
    this.context = context;
  }

  static async put(key: string, value: string): Promise<void> {
    try {
      const preferences = await preferences.getPreferences(this.context, 'stock_app');
      await preferences.put(key, value);
      await preferences.flush();
    } catch (err) {
      console.error('PreferenceUtil put error:', err);
    }
  }

  static async get(key: string, defaultValue: string = ''): Promise<string> {
    try {
      const preferences = await preferences.getPreferences(this.context, 'stock_app');
      return await preferences.get(key, defaultValue) as string;
    } catch (err) {
      console.error('PreferenceUtil get error:', err);
      return defaultValue;
    }
  }

  static async delete(key: string): Promise<void> {
    try {
      const preferences = await preferences.getPreferences(this.context, 'stock_app');
      await preferences.delete(key);
      await preferences.flush();
    } catch (err) {
      console.error('PreferenceUtil delete error:', err);
    }
  }

  static async clear(): Promise<void> {
    try {
      const preferences = await preferences.getPreferences(this.context, 'stock_app');
      await preferences.clear();
      await preferences.flush();
    } catch (err) {
      console.error('PreferenceUtil clear error:', err);
    }
  }
}
