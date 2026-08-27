declare namespace Zotero {
  interface Item {
    id: number;
    key: string;
    version: number;
    libraryID: number;
    isRegularItem(): boolean;
    isFeedItem: boolean;
    isAttachment(): boolean;
    isNote(): boolean;
    itemType: string;
    getField(name: string, unformatted?: boolean, includeBaseMapped?: boolean): string;
    getTags(): Array<{ tag: string; type?: number }>;
    addTag(tag: string, type?: number): void;
    removeTag(tag: string): void;
    getAttachments(includeTrash?: boolean): number[];
    saveTx(options?: any): Promise<number | boolean>;
    toJSON(): Record<string, any>;
  }

  namespace Items {
    function get(id: number): Item | false;
    function getAsync(ids: number | number[]): Promise<Item | Item[]>;
    function getTop(libraryID?: number): Promise<Item[]>;
  }

  namespace Notifier {
    type EventType = 'add' | 'modify' | 'delete' | 'move' | 'trash' | 'refresh';
    type ItemType = 'item' | 'collection' | 'search' | 'item-tag' | 'tag' | 'feedItem';
    
    interface Observer {
      notify(event: EventType, type: ItemType, ids: (string | number)[], extraData: Record<string, any>): void;
    }

    function registerObserver(observer: Observer, types?: ItemType[], name?: string): string;
    function unregisterObserver(id: string): void;
  }

  namespace ItemPaneManager {
    interface SectionOptions {
      paneID: string;
      pluginID: string;
      header: {
        l10nID?: string;
        label?: string;
        icon?: string;
      };
      sidenav: {
        l10nID?: string;
        label?: string;
        icon?: string;
      };
      onRender?: (params: {
        body: HTMLElement;
        item: Item;
        editable?: boolean;
        tabType?: string;
      }) => void | Promise<void>;
      onAsyncRender?: (params: {
        body: HTMLElement;
        item: Item;
        editable?: boolean;
        tabType?: string;
      }) => Promise<void>;
      onInit?: () => void;
      onDestroy?: () => void;
    }

    function registerSection(options: SectionOptions): string;
    function unregisterSection(paneID: string): void;
  }

  namespace PreferencePanes {
    interface PaneOptions {
      pluginID: string;
      src: string;
      label: string;
      image?: string;
      defaultXUL?: boolean;
      stylesheets?: string[];
      helpURL?: string;
    }

    function register(options: PaneOptions): void;
    function unregister(pluginID: string): void;
  }

  namespace Prefs {
    function get(name: string, isGlobal?: boolean): any;
    function set(name: string, value: any, isGlobal?: boolean): void;
    function registerObserver(name: string, handler: (name: string) => void): symbol;
    function unregisterObserver(symbol: symbol): void;
  }

  class DBConnection {
    constructor(name: string);
    queryAsync(sql: string, params?: any[]): Promise<any[]>;
    executeTransaction(callback: () => Promise<void>): Promise<void>;
    close(): Promise<void>;
  }

  namespace DataDirectory {
    const dir: string;
  }

  function log(message: string): void;
  function warn(message: string): void;
  function debug(message: string): void;
}

declare const IOUtils: {
  readUTF8(path: string): Promise<string>;
  writeUTF8(path: string, content: string, options?: any): Promise<void>;
  makeDirectory(path: string, options?: any): Promise<void>;
  exists(path: string): Promise<boolean>;
};

declare const PathUtils: {
  join(...args: string[]): string;
  parent(path: string): string;
  filename(path: string): string;
};

declare const Services: {
  scriptloader: {
    loadSubScript(url: string, targetScope?: any): void;
  };
};

declare const ZoteroPane: {
  getSelectedItems(): Zotero.Item[];
};
