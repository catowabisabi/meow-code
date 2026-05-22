import { writeFile, readFile, chmod } from "fs/promises";
import { existsSync } from "fs";
import path from "path";
import crypto from "crypto";

const CONFIG_PATH = path.join(process.env.HOME || "~", ".cato", "config.json");

export interface ConfigStoreData {
  model?: string;
  baseUrl?: string;
  [key: string]: unknown;
}

interface StoredConfig {
  version: number;
  checksum: string;
  data: ConfigStoreData;
}

function computeChecksum(data: ConfigStoreData): string {
  const content = JSON.stringify(data);
  return crypto.createHash("sha256").update(content).digest("hex");
}

function verifyChecksum(data: ConfigStoreData, checksum: string): boolean {
  return computeChecksum(data) === checksum;
}

export class ConfigStore {
  private cache: ConfigStoreData | null = null;

  private async ensureConfigDir(): Promise<void> {
    const dir = path.dirname(CONFIG_PATH);
    if (!existsSync(dir)) {
      const { mkdir } = await import("fs/promises");
      await mkdir(dir, { recursive: true });
    }
  }

  async loadConfig(): Promise<ConfigStoreData> {
    if (this.cache) {
      return this.cache;
    }

    if (!existsSync(CONFIG_PATH)) {
      this.cache = {};
      return this.cache;
    }

    try {
      const raw = await readFile(CONFIG_PATH, "utf-8");
      const stored: StoredConfig = JSON.parse(raw);

      if (!verifyChecksum(stored.data, stored.checksum)) {
        throw new Error("Config checksum mismatch");
      }

      this.cache = stored.data;
      return this.cache;
    } catch {
      this.cache = {};
      return this.cache;
    }
  }

  async saveConfig(data: ConfigStoreData): Promise<void> {
    await this.ensureConfigDir();

    const stored: StoredConfig = {
      version: 1,
      checksum: computeChecksum(data),
      data,
    };

    await writeFile(CONFIG_PATH, JSON.stringify(stored, null, 2), "utf-8");
    await chmod(CONFIG_PATH, 0o600);
    this.cache = data;
  }

  async setKey(key: string, value: unknown): Promise<void> {
    const data = await this.loadConfig();
    data[key] = value;
    await this.saveConfig(data);
  }

  async getKey(key: string): Promise<unknown> {
    const data = await this.loadConfig();
    return data[key];
  }

  async deleteKey(key: string): Promise<void> {
    const data = await this.loadConfig();
    delete data[key];
    await this.saveConfig(data);
  }

  async setModel(model: string): Promise<void> {
    await this.setKey("model", model);
  }

  async getModel(): Promise<string | undefined> {
    return (await this.loadConfig()).model;
  }

  async setBaseUrl(baseUrl: string): Promise<void> {
    await this.setKey("baseUrl", baseUrl);
  }

  async getBaseUrl(): Promise<string | undefined> {
    return (await this.loadConfig()).baseUrl;
  }
}

export const configStore = new ConfigStore();