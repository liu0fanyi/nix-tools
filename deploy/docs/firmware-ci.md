# 统一设备豆 CI 上传通道

权威规格：[基础设施009](../../specs/009-infrastructure/spec.md)；固件CI与主线任务在 esp32-device-bean/001。

计划安装目录：`/usr/local/libexec/device-bean-firmware/`，只放经过本机回归的 `firmware-receive.py` 与 `publish-firmware.py`。目录/脚本归root所有且不可由其他用户写；接收器使用固定ESP32目录，保留原发布事务。安装前保存现有同名文件（若存在）并核对，不做全量infra部署或容器重启。

独立SSH key只授权公钥到阿里云，authorized_keys条目为：

```text
restrict,command="/usr/bin/python3 -I /usr/local/libexec/device-bean-firmware/firmware-receive.py" ssh-ed25519 <专用上传公钥> device-bean-firmware-ci
```

保留所有既有authorized_keys条目；不复用Android/Clip key。私钥保存本机私有位置及GitHub固件专用environment secret `FIRMWARE_UPLOAD_KEY`，不放阿里云、不提交。候选客户端固定服务器公钥，命令只能是 `firmware-publish`，stdin仅有界JSON。`read`只读catalog；`assets`不更新catalog；`catalog`校验已有资产与旧摘要后原子合并。

接收器校验产品、来源、大小/摘要、目录和不覆盖边界；候选的密码学验签由固定common打包工具在CI完成，设备升级时再次按既有信任根验签。不要把服务端对 signingKeyId 字段的检查描述成服务端密码学验签。

启用前先通过专用key执行只读read，确认任意shell、旧产品和任意路径请求被拒绝；确认其他目录/授权未改。随后真实CI先传不可变镜像，公网大小/SHA回查成功后才CAS更新catalog，再回查目录。失败保留旧catalog，不删除历史制品。

本轮状态：实现和13项事务/接收器测试通过；服务端安装、凭据、CI实际发布仍待执行。GitHub指定审批人规则受套餐限制；采用仅main分支的环境方案需先核对限制实际生效，再保存签名秘密，不能用无保护空环境兜底。
