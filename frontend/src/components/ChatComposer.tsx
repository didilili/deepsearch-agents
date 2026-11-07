import {
  PaperClipOutlined,
  PlusOutlined,
  SendOutlined,
  StopOutlined
} from "@ant-design/icons";
import { Button, Tooltip, Upload } from "antd";
import type { UploadFile } from "antd";
import type { UploadedItem } from "../types";

interface ChatComposerProps {
  isCancelling: boolean;
  isRunning: boolean;
  isUploading: boolean;
  onNewSession: () => void;
  onCancel: () => void;
  onQueryChange: (value: string) => void;
  onSubmit: () => void;
  onUpload: (items: UploadedItem[]) => Promise<void> | void;
  query: string;
  stagedItems: UploadedItem[];
  uploadedItems: UploadedItem[];
  onStagedItemsChange: (items: UploadedItem[]) => void;
  onRemoveAttachment: (filename: string) => Promise<void>;
  removingFilename: string | null;
}

function toUploadedItem(file: UploadFile): UploadedItem | null {
  if (!file.originFileObj) {
    return null;
  }

  return {
    uid: file.uid,
    name: file.name,
    size: file.size || 0,
    raw: file.originFileObj
  };
}

function uniqueUploadedItems(items: UploadedItem[]): UploadedItem[] {
  const names = new Set<string>();
  return items.filter((item) => {
    if (names.has(item.name)) {
      return false;
    }
    names.add(item.name);
    return true;
  });
}

export function ChatComposer({
  isCancelling,
  isRunning,
  isUploading,
  onCancel,
  onNewSession,
  onQueryChange,
  onRemoveAttachment,
  onStagedItemsChange,
  onSubmit,
  onUpload,
  query,
  stagedItems,
  uploadedItems,
  removingFilename
}: ChatComposerProps) {
  const hasStagedFiles = stagedItems.length > 0;
  const canSubmit = query.trim().length > 0;
  const isRemovingAttachment = removingFilename !== null;

  function handleAttachmentChange(fileList: UploadFile[]) {
    const nextItems = uniqueUploadedItems(
      fileList
        .map(toUploadedItem)
        .filter((item): item is UploadedItem => Boolean(item))
    );

    if (nextItems.length === 0) {
      return;
    }

    onStagedItemsChange(nextItems);
    void Promise.resolve(onUpload(nextItems)).finally(() => {
      onStagedItemsChange([]);
    });
  }

  return (
    <section className="chat-composer" aria-label="发送研搜任务">
      {uploadedItems.length > 0 ? (
        <div className="attachment-strip" aria-label="当前会话附件">
          {uploadedItems.map((item) => (
            <span className="attachment-pill" key={`${item.uid}-${item.name}`}>
              <PaperClipOutlined aria-hidden />
              <span className="attachment-name">{item.name}</span>
              <Button
                aria-label={`移除附件 ${item.name}`}
                disabled={isRunning || isUploading || isRemovingAttachment}
                loading={removingFilename === item.name}
                onClick={() => void onRemoveAttachment(item.name)}
                size="small"
                type="text"
              >
                移除
              </Button>
            </span>
          ))}
        </div>
      ) : null}

      {hasStagedFiles ? (
        <div className="attachment-strip" aria-label="待上传附件">
          {stagedItems.map((item) => (
            <span className="attachment-pill attachment-pill--pending" key={item.uid}>
              <PaperClipOutlined aria-hidden />
              {item.name}
            </span>
          ))}
          {isUploading ? <span className="attachment-uploading">附着中...</span> : null}
        </div>
      ) : null}

      <div className="composer-shell">
        <textarea
          aria-label="研搜任务"
          disabled={isRunning || isRemovingAttachment}
          onChange={(event) => onQueryChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              onSubmit();
            }
          }}
          placeholder="向 DeepSearch Agents 发送任务..."
          value={query}
        />

        <div className="composer-toolbar">
          <div className="composer-left-actions">
            <Tooltip title="新建会话">
              <Button
                aria-label="新建会话"
                className="composer-icon-button"
                disabled={isRemovingAttachment}
                icon={<PlusOutlined />}
                onClick={onNewSession}
                shape="circle"
              />
            </Tooltip>
            <Upload
              beforeUpload={() => false}
              fileList={[]}
              multiple
              onChange={(info) => {
                handleAttachmentChange(info.fileList.length > 0 ? info.fileList : [info.file]);
              }}
              showUploadList={false}
            >
              <Tooltip title="选择附件">
                <Button
                  aria-label="选择附件"
                  className="composer-icon-button"
                  disabled={isRunning || isUploading || isRemovingAttachment}
                  icon={<PaperClipOutlined />}
                  shape="circle"
                />
              </Tooltip>
            </Upload>
          </div>

          <Tooltip title={isRunning ? "取消当前任务" : "发送任务"}>
            <Button
              aria-label={isRunning ? "取消当前任务" : "发送任务"}
              className={isRunning ? "send-button send-button--cancel" : "send-button"}
              disabled={isRunning ? isCancelling : !canSubmit || isRemovingAttachment}
              icon={isRunning ? <StopOutlined /> : <SendOutlined />}
              loading={isCancelling}
              onClick={isRunning ? onCancel : onSubmit}
              shape="circle"
              type="primary"
            />
          </Tooltip>
        </div>
      </div>
    </section>
  );
}
