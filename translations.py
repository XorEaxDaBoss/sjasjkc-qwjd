MESSAGES = {
    'en': {
        'welcome': "👋 Welcome! I'm your CC Cleaning Assistant\n\n"
                  "I help format and validate your CC data efficiently. You can:\n"
                  "• Send CCs directly in text format\n"
                  "• Upload file(s) containing CC data\n"
                  "• Use /bin command to lookup BIN info\n"
                  "  Example: /bin 123456 or /bin 123456,789012\n\n"
                  "📝 Note: When uploading multiple files, please send them together in a single message for best results.\n\n"
                  "Join @Cvv_Shops to get updates on new features.\n\n"
                  "Choose an option to begin!",
        'clean_ccs': "Please send your CC data. You can:\n"
                    "• Send text directly\n"
                    "• Upload file(s) containing CC data\n\n"
                    "I'll clean and format everything for you.",
        'filter_bin': "Please send your CC data. You can:\n"
                     "• Send text directly\n"
                     "• Upload file(s) containing CC data\n\n"
                     "I'll clean and sort everything by BIN for you.",
        'broadcast': "📢 Please send the message you want to broadcast to all users.\n"
                    "Your next message will be sent to everyone.\n"
                    "Use /cancel to cancel the broadcast.",
        'broadcast_message': "{}",
        'broadcasting': "📢 Broadcasting message to all users...",
        'broadcast_status': "📢 Broadcast in progress... Sent to {} users",
        'broadcast_completed': "📢 Broadcast completed!\nSuccess: {}\nFailed: {}",
        'broadcast_cancelled': "📢 Broadcast cancelled.",
        'unknown_command': "Unknown command",
        'invalid_file': "❌ Please send a .txt file.",
        'file_too_large': "❌ File too large. Maximum size is 20MB.",
        'no_valid_cards': "❌ No valid card data found in file.",
        'filtered_bins_caption': "🎯 Filtered BINs Results:\nTotal CCs: {}\nUnique BINs: {}",
        'cleaned_ccs_caption': "🧹 Clean CCs: {}",
        'forwarded_caption': "{} from @{}",
        'choose_option': "Please choose an option to continue:",
        'invalid_broadcast': "❌ Invalid broadcast message. Please send a text message.",
        'owner_only': "⚠️ This command is only available to the bot owner.",
        # Button texts
        'btn_clean': "🧹 Clean CCs",
        'btn_filter_bin': "🔍 Filter by BIN",
        'btn_broadcast': "📢 Broadcast",
        'btn_language': "中文 🇨🇳",  # Shows Chinese option when in English
        'bin_prompt': "Please provide a BIN number.\nExample: /bin 123456 or /bin 123456,789012",
        'invalid_bin': "Invalid BIN: {}. BIN must be 6 digits.",
        'bin_not_found': "No information found for BIN: {}",
        'bin_result': "🔍 BIN Lookup Result\n\n"
                     "➜ BIN: {}\n\n"
                     "➜ Info: {} - {} - {}\n"
                     "➜ Issuer: {}\n"
                     "➜ Country: {} {}\n\n"
                     "Checked by @cleancc_bot",
        'error_occurred': "An error occurred. Please try again.",
        'user_not_identified': "Error: Could not identify user.",
        'language_changed': "Language changed to English 🇺🇸",
    },
    'zh': {
        'welcome': "👋 欢迎！我是您的信用卡清理助手\n\n"
                  "我可以帮助您高效地格式化和验证信用卡数据。您可以：\n"
                  "• 直接以文本格式发送信用卡信息\n"
                  "• 上传包含信用卡数据的文件\n"
                  "• 使用 /bin 命令查询 BIN 信息\n"
                  "  示例：/bin 123456 或 /bin 123456,789012\n\n"
                  "📝 注意：上传多个文件时，请在同一条消息中一起发送以获得最佳结果。\n\n"
                  "加入 @Cvv_Shops 获取新功能更新。\n\n"
                  "选择一个选项开始！",
        'clean_ccs': "请发送您的信用卡数据。您可以：\n"
                    "• 直接发送文本\n"
                    "• 上传包含信用卡数据的文件\n\n"
                    "我会为您清理和格式化所有内容。",
        'filter_bin': "请发送您的信用卡数据。您可以：\n"
                     "• 直接发送文本\n"
                     "• 上传包含信用卡数据的文件\n\n"
                     "我会为您按BIN整理所有内容。",
        'broadcast': "📢 请发送您要广播给所有用户的消息。\n"
                    "您的下一条消息将发送给所有人。\n"
                    "使用 /cancel 取消广播。",
        'broadcast_message': "{}",
        'broadcasting': "📢 正在向所有用户广播消息...",
        'broadcast_status': "📢 广播进行中... 已发送给 {} 位用户",
        'broadcast_completed': "📢 广播完成！\n成功：{}\n失败：{}",
        'broadcast_cancelled': "📢 广播已取消。",
        'unknown_command': "未知命令",
        'invalid_file': "❌ 请发送.txt文件。",
        'file_too_large': "❌ 文件太大。最大大小为20MB。",
        'no_valid_cards': "❌ 文件中未找到有效的卡数据。",
        'filtered_bins_caption': "🎯 BIN筛选结果：\n总卡数：{}\n唯一BIN数：{}",
        'cleaned_ccs_caption': "🧹 已清理卡数：{}",
        'forwarded_caption': "{} 来自 @{}",
        'choose_option': "请选择一个选项继续：",
        'invalid_broadcast': "❌ 无效的广播消息。请发送文本消息。",
        'owner_only': "⚠️ 此命令仅供机器人所有者使用。",
        # Button texts
        'btn_clean': "🧹 清理信用卡",
        'btn_filter_bin': "🔍 按BIN筛选",
        'btn_broadcast': "📢 广播消息",
        'btn_language': "English 🇺🇸",  # Shows English option when in Chinese
        'bin_prompt': "请提供一个 BIN 号码。\n示例：/bin 123456 或 /bin 123456,789012",
        'invalid_bin': "无效的 BIN：{}。BIN 必须是6位数字。",
        'bin_not_found': "未找到 BIN：{} 的相关信息",
        'bin_result': "🔍 BIN 查询结果\n\n"
                     "➜ BIN：{}\n\n"
                     "➜ 信息：{} - {} - {}\n"
                     "➜ 发卡行：{}\n"
                     "➜ 国家：{} {}\n\n"
                     "由 @cleancc_bot 查询",
        'error_occurred': "发生错误。请重试。",
        'user_not_identified': "错误：无法识别用户。",
        'language_changed': "语言已更改为中文 🇨🇳",
    }
}
