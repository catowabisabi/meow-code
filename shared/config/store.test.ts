import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";

const mockWriteFile = vi.fn();
const mockReadFile = vi.fn();
const mockChmod = vi.fn();
const mockExistsSync = vi.fn();
const mockMkdir = vi.fn();

vi.mock("fs/promises", () => ({
  writeFile: mockWriteFile,
  readFile: mockReadFile,
  chmod: mockChmod,
  mkdir: mockMkdir,
}));

vi.mock("fs", () => ({
  existsSync: mockExistsSync,
}));

describe("ConfigStore", () => {
  let ConfigStore: any;
  let configStore: any;

  beforeEach(async () => {
    vi.clearAllMocks();
    vi.resetModules();
    const module = await import("./store");
    ConfigStore = module.ConfigStore;
    configStore = new ConfigStore();
  });

  describe("loadConfig", () => {
    it("returns empty object when config file does not exist", async () => {
      mockExistsSync.mockReturnValue(false);

      const result = await configStore.loadConfig();

      expect(result).toEqual({});
    });

    it("loads and parses existing config with valid checksum", async () => {
      mockExistsSync.mockReturnValue(true);
      const storedData = { model: "gpt-4", baseUrl: "https://api.example.com" };
      const checksum = "a".repeat(64); // dummy checksum for test
      mockReadFile.mockResolvedValue(
        JSON.stringify({
          version: 1,
          checksum,
          data: storedData,
        })
      );

      // Mock the actual checksum verification
      vi.spyOn(configStore as any, "computeChecksum").mockReturnValue(checksum);

      const result = await configStore.loadConfig();

      expect(result).toEqual(storedData);
    });

    it("returns empty object on checksum mismatch", async () => {
      mockExistsSync.mockReturnValue(true);
      const storedData = { model: "gpt-4" };
      mockReadFile.mockResolvedValue(
        JSON.stringify({
          version: 1,
          checksum: "invalid-checksum",
          data: storedData,
        })
      );

      const result = await configStore.loadConfig();

      expect(result).toEqual({});
    });

    it("returns empty object on parse error", async () => {
      mockExistsSync.mockReturnValue(true);
      mockReadFile.mockRejectedValue(new Error("ENOENT"));

      const result = await configStore.loadConfig();

      expect(result).toEqual({});
    });
  });

  describe("saveConfig", () => {
    it("writes config with checksum and sets file permissions to 0o600", async () => {
      mockExistsSync.mockReturnValue(true);
      mockWriteFile.mockResolvedValue(undefined);
      mockChmod.mockResolvedValue(undefined);

      const data = { model: "gpt-4", baseUrl: "https://api.example.com" };
      await configStore.saveConfig(data);

      expect(mockWriteFile).toHaveBeenCalled();
      const writtenContent = JSON.parse(mockWriteFile.mock.calls[0][1]);
      expect(writtenContent).toHaveProperty("version", 1);
      expect(writtenContent).toHaveProperty("checksum");
      expect(writtenContent).toHaveProperty("data", data);
      expect(mockChmod).toHaveBeenCalledWith(expect.any(String), 0o600);
    });

    it("creates config directory if it does not exist", async () => {
      mockExistsSync.mockReturnValue(false);
      mockWriteFile.mockResolvedValue(undefined);
      mockChmod.mockResolvedValue(undefined);
      mockMkdir.mockResolvedValue(undefined);

      await configStore.saveConfig({ model: "gpt-4" });

      expect(mockMkdir).toHaveBeenCalled();
    });
  });

  describe("setKey / getKey", () => {
    it("sets and gets a string key", async () => {
      mockExistsSync.mockReturnValue(false);
      mockWriteFile.mockResolvedValue(undefined);
      mockChmod.mockResolvedValue(undefined);

      await configStore.setKey("testKey", "testValue");
      const value = await configStore.getKey("testKey");

      expect(value).toBe("testValue");
    });

    it("sets and gets a nested object", async () => {
      mockExistsSync.mockReturnValue(false);
      mockWriteFile.mockResolvedValue(undefined);
      mockChmod.mockResolvedValue(undefined);

      const nestedObj = { a: 1, b: { c: 2 } };
      await configStore.setKey("nested", nestedObj);
      const value = await configStore.getKey("nested");

      expect(value).toEqual(nestedObj);
    });
  });

  describe("deleteKey", () => {
    it("deletes an existing key", async () => {
      mockExistsSync.mockReturnValue(true);
      mockWriteFile.mockResolvedValue(undefined);
      mockChmod.mockResolvedValue(undefined);
      const initialData = { model: "gpt-4", baseUrl: "https://api.example.com" };
      const checksum = "a".repeat(64);
      mockReadFile.mockResolvedValue(
        JSON.stringify({
          version: 1,
          checksum,
          data: initialData,
        })
      );
      vi.spyOn(configStore as any, "computeChecksum").mockReturnValue(checksum);

      await configStore.deleteKey("baseUrl");
      const value = await configStore.getKey("baseUrl");

      expect(value).toBeUndefined();
    });
  });

  describe("setModel / getModel", () => {
    it("sets and gets model", async () => {
      mockExistsSync.mockReturnValue(false);
      mockWriteFile.mockResolvedValue(undefined);
      mockChmod.mockResolvedValue(undefined);

      await configStore.setModel("gpt-4o");
      const model = await configStore.getModel();

      expect(model).toBe("gpt-4o");
    });
  });

  describe("setBaseUrl / getBaseUrl", () => {
    it("sets and gets baseUrl", async () => {
      mockExistsSync.mockReturnValue(false);
      mockWriteFile.mockResolvedValue(undefined);
      mockChmod.mockResolvedValue(undefined);

      await configStore.setBaseUrl("https://api.example.com");
      const baseUrl = await configStore.getBaseUrl();

      expect(baseUrl).toBe("https://api.example.com");
    });
  });
});