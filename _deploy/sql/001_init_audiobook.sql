-- =============================================================================
-- 听书商城智能客服 —— 业务后端数据库初始化脚本
-- 目标库：audiobook（与虚拟主机 192.168.200.10:3307 上的实际库结构一致）
-- 说明：重建听书场景所需表结构并写入种子数据，可重复执行（会清空旧表）。
-- =============================================================================

SET NAMES utf8mb4;

CREATE DATABASE IF NOT EXISTS `audiobook`
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE `audiobook`;

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `handoff_requests`;
DROP TABLE IF EXISTS `refund_requests`;
DROP TABLE IF EXISTS `chapters`;
DROP TABLE IF EXISTS `coupon_redemptions`;
DROP TABLE IF EXISTS `coupons`;
DROP TABLE IF EXISTS `vip_memberships`;
DROP TABLE IF EXISTS `order_items`;
DROP TABLE IF EXISTS `orders`;
DROP TABLE IF EXISTS `books`;
DROP TABLE IF EXISTS `users`;

SET FOREIGN_KEY_CHECKS = 1;

-- -----------------------------------------------------------------------------
-- 用户表
-- -----------------------------------------------------------------------------
CREATE TABLE `users` (
  `id`            BIGINT        NOT NULL AUTO_INCREMENT,
  `user_id`       VARCHAR(64)   NOT NULL,
  `nickname`      VARCHAR(100)  NOT NULL,
  `level`         VARCHAR(32)   NOT NULL,
  `mobile_masked` VARCHAR(32)   NOT NULL,
  `created_at`    DATETIME      NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `user_id` (`user_id`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------
-- 有声书表
-- -----------------------------------------------------------------------------
CREATE TABLE `books` (
  `id`               BIGINT         NOT NULL AUTO_INCREMENT,
  `book_id`          VARCHAR(64)    NOT NULL,
  `title`            VARCHAR(255)   NOT NULL,
  `author`           VARCHAR(255)   NOT NULL,
  `narrator`         VARCHAR(255)   NOT NULL,
  `category`         VARCHAR(64)    NOT NULL,
  `description`      TEXT           NOT NULL,
  `price`            DECIMAL(10, 2) NOT NULL,
  `chapter_count`    INT            NOT NULL,
  `duration_minutes` INT            NOT NULL,
  `cover_url`        VARCHAR(500)   DEFAULT NULL,
  `attributes_json`  JSON           NOT NULL,
  `created_at`       DATETIME       NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `book_id` (`book_id`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------
-- 订单表
-- -----------------------------------------------------------------------------
CREATE TABLE `orders` (
  `id`          BIGINT         NOT NULL AUTO_INCREMENT,
  `order_id`    VARCHAR(64)    NOT NULL,
  `user_id`     BIGINT         NOT NULL,
  `status`      VARCHAR(32)    NOT NULL,
  `status_desc` VARCHAR(255)   NOT NULL,
  `amount`      DECIMAL(10, 2) NOT NULL,
  `created_at`  DATETIME       NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `order_id` (`order_id`),
  KEY `fk_orders_user` (`user_id`),
  CONSTRAINT `fk_orders_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------
-- 订单明细表
-- -----------------------------------------------------------------------------
CREATE TABLE `order_items` (
  `id`             BIGINT         NOT NULL AUTO_INCREMENT,
  `order_id`       BIGINT         NOT NULL,
  `book_id`        BIGINT         NOT NULL,
  `title_snapshot` VARCHAR(255)   NOT NULL,
  `quantity`       INT            NOT NULL,
  `price`          DECIMAL(10, 2) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_order_items_order` (`order_id`),
  KEY `fk_order_items_book` (`book_id`),
  CONSTRAINT `fk_order_items_book` FOREIGN KEY (`book_id`) REFERENCES `books` (`id`),
  CONSTRAINT `fk_order_items_order` FOREIGN KEY (`order_id`) REFERENCES `orders` (`id`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------
-- 会员表
-- -----------------------------------------------------------------------------
CREATE TABLE `vip_memberships` (
  `id`                          BIGINT      NOT NULL AUTO_INCREMENT,
  `user_id`                     BIGINT      NOT NULL,
  `vip_status`                  VARCHAR(32) NOT NULL,
  `remaining_listening_minutes` INT         NOT NULL,
  `started_at`                  DATETIME    NOT NULL,
  `expires_at`                  DATETIME    NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_vip_memberships_user` (`user_id`),
  CONSTRAINT `fk_vip_memberships_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------
-- 优惠券表
-- -----------------------------------------------------------------------------
CREATE TABLE `coupons` (
  `id`             BIGINT         NOT NULL AUTO_INCREMENT,
  `coupon_code`    VARCHAR(64)    NOT NULL,
  `coupon_info`    VARCHAR(255)   NOT NULL,
  `discount_type`  VARCHAR(32)    NOT NULL,
  `discount_value` DECIMAL(10, 2) NOT NULL,
  `status`         VARCHAR(32)    NOT NULL,
  `expires_at`     DATETIME       NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `coupon_code` (`coupon_code`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------
-- 优惠券兑换记录表
-- -----------------------------------------------------------------------------
CREATE TABLE `coupon_redemptions` (
  `id`            BIGINT       NOT NULL AUTO_INCREMENT,
  `redemption_id` VARCHAR(64)  NOT NULL,
  `coupon_id`     BIGINT       NOT NULL,
  `user_id`       BIGINT       NOT NULL,
  `operator`      VARCHAR(64)  NOT NULL,
  `status`        VARCHAR(32)  NOT NULL,
  `status_desc`   VARCHAR(255) NOT NULL,
  `created_at`    DATETIME     NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `redemption_id` (`redemption_id`),
  KEY `fk_coupon_redemptions_coupon` (`coupon_id`),
  KEY `fk_coupon_redemptions_user` (`user_id`),
  CONSTRAINT `fk_coupon_redemptions_coupon` FOREIGN KEY (`coupon_id`) REFERENCES `coupons` (`id`),
  CONSTRAINT `fk_coupon_redemptions_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------
-- 章节表
-- -----------------------------------------------------------------------------
CREATE TABLE `chapters` (
  `id`               BIGINT       NOT NULL AUTO_INCREMENT,
  `book_id`          BIGINT       NOT NULL,
  `chapter_number`   INT          NOT NULL,
  `title`            VARCHAR(255) NOT NULL,
  `duration_minutes` INT          NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_chapters_book` (`book_id`),
  CONSTRAINT `fk_chapters_book` FOREIGN KEY (`book_id`) REFERENCES `books` (`id`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------
-- 退款申请表
-- -----------------------------------------------------------------------------
CREATE TABLE `refund_requests` (
  `id`          BIGINT       NOT NULL AUTO_INCREMENT,
  `refund_id`   VARCHAR(64)  NOT NULL,
  `order_id`    BIGINT       NOT NULL,
  `operator`    VARCHAR(64)  NOT NULL,
  `reason`      VARCHAR(255) NOT NULL,
  `status`      VARCHAR(32)  NOT NULL,
  `status_desc` VARCHAR(255) NOT NULL,
  `created_at`  DATETIME     NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `refund_id` (`refund_id`),
  KEY `fk_refund_order` (`order_id`),
  CONSTRAINT `fk_refund_order` FOREIGN KEY (`order_id`) REFERENCES `orders` (`id`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------
-- 人工客服转接表
-- -----------------------------------------------------------------------------
CREATE TABLE `handoff_requests` (
  `id`          BIGINT       NOT NULL AUTO_INCREMENT,
  `handoff_id`  VARCHAR(64)  NOT NULL,
  `user_id`     BIGINT       NOT NULL,
  `reason`      VARCHAR(255) NOT NULL,
  `status`      VARCHAR(32)  NOT NULL,
  `status_desc` VARCHAR(255) NOT NULL,
  `created_at`  DATETIME     NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `handoff_id` (`handoff_id`),
  KEY `fk_handoff_user` (`user_id`),
  CONSTRAINT `fk_handoff_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- =============================================================================
-- 种子数据
-- =============================================================================

INSERT INTO `users` (`id`, `user_id`, `nickname`, `level`, `mobile_masked`, `created_at`) VALUES
  (1, 'u1001', '小李', 'VIP会员',  '138****1234', '2026-04-01 09:00:00'),
  (2, 'u1002', '王敏', '普通会员', '139****5678', '2026-04-02 10:30:00'),
  (3, 'u1003', '陈晨', 'VIP会员',  '137****2468', '2026-04-03 19:20:00');

INSERT INTO `books` (`id`, `book_id`, `title`, `author`, `narrator`, `category`, `description`, `price`, `chapter_count`, `duration_minutes`, `cover_url`, `attributes_json`, `created_at`) VALUES
  (1, 'BOOK10001', '三体',         '刘慈欣',         '王明军', '科幻', '地球文明与三体文明的信息交流与生死搏杀，以及两个文明在宇宙中的兴衰历程。', 59.90, 30,  1200, 'https://example.com/images/three-body.jpg',     '{"语种": "中文", "出品方": "喜马拉雅", "是否完结": "已完结", "更新状态": "全集"}', '2026-03-20 12:00:00'),
  (2, 'BOOK10002', '明朝那些事儿', '当年明月',       '赵乾景', '历史', '以史料为基础，用轻松幽默的笔触讲述明朝三百年的历史风云。',                     49.90, 200, 3600, 'https://example.com/images/ming-dynasty.jpg',   '{"语种": "中文", "出品方": "懒人听书", "是否完结": "已完结", "更新状态": "全集"}', '2026-03-22 14:00:00'),
  (3, 'BOOK10003', '活着',         '余华',           '李野墨', '文学', '讲述在大时代背景下，主人公徐福贵充满苦难与坚韧的一生。',                         29.90, 20,  400,  'https://example.com/images/to-live.jpg',        '{"语种": "中文", "出品方": "喜马拉雅", "是否完结": "已完结", "更新状态": "全集"}', '2026-03-25 08:30:00'),
  (4, 'BOOK10004', '平凡的世界',   '路遥',           '董卿',   '小说', '全景式展现中国当代城乡社会生活，讲述普通人在大时代中的奋斗历程。',               39.90, 162, 2800, 'https://example.com/images/ordinary-world.jpg', '{"语种": "中文", "出品方": "蜻蜓FM", "是否完结": "已完结", "更新状态": "全集"}', '2026-03-27 11:10:00'),
  (5, 'BOOK10005', '人类简史',     '尤瓦尔·赫拉利', '康辉',   '历史', '从认知革命、农业革命到科技革命，重新审视智人如何主宰地球。',                     45.00, 20,  900,  'https://example.com/images/sapiens.jpg',        '{"语种": "中文", "出品方": "喜马拉雅", "是否完结": "已完结", "更新状态": "全集"}', '2026-03-29 16:20:00'),
  (6, 'BOOK10006', '富爸爸穷爸爸', '罗伯特·清崎',   '梁宏达', '商业', '通过对比两位爸爸的金钱观，帮助你建立正确的财富观念与理财思维。',                 25.00, 18,  500,  'https://example.com/images/rich-dad.jpg',       '{"语种": "中文", "出品方": "懒人听书", "是否完结": "已完结", "更新状态": "全集"}', '2026-03-30 13:40:00');

INSERT INTO `orders` (`id`, `order_id`, `user_id`, `status`, `status_desc`, `amount`, `created_at`) VALUES
  (1, 'A20260410001', 1, '已完成', '订单已完成，听书已解锁，可随时收听。', 59.90, '2026-04-10 10:00:00'),
  (2, 'A20260408002', 1, '已完成', '订单已完成，听书已解锁，可随时收听。', 49.90, '2026-04-08 15:30:00'),
  (3, 'A20260405003', 1, '已退款', '订单已退款，款项已原路退回。',         29.90, '2026-04-05 11:20:00'),
  (4, 'A20260407004', 1, '已完成', '订单已完成，听书已解锁，可随时收听。', 39.90, '2026-04-07 18:15:00'),
  (5, 'A20260402005', 1, '已取消', '订单已取消，听书未解锁。',             45.00, '2026-04-02 09:45:00'),
  (6, 'B20260409001', 2, '已完成', '订单已完成，听书已解锁，可随时收听。', 25.00, '2026-04-09 20:30:00'),
  (7, 'B20260401002', 2, '待支付', '订单待支付，请尽快完成付款。',         29.90, '2026-04-01 14:05:00'),
  (8, 'C20260406001', 3, '已完成', '订单已完成，听书已解锁，可随时收听。', 49.90, '2026-04-06 12:25:00');

INSERT INTO `order_items` (`id`, `order_id`, `book_id`, `title_snapshot`, `quantity`, `price`) VALUES
  (1, 1, 1, '三体',         1, 59.90),
  (2, 2, 2, '明朝那些事儿', 1, 49.90),
  (3, 3, 3, '活着',         1, 29.90),
  (4, 4, 4, '平凡的世界',   1, 39.90),
  (5, 5, 5, '人类简史',     1, 45.00),
  (6, 6, 6, '富爸爸穷爸爸', 1, 25.00),
  (7, 7, 3, '活着',         1, 29.90),
  (8, 8, 2, '明朝那些事儿', 1, 49.90);

INSERT INTO `vip_memberships` (`id`, `user_id`, `vip_status`, `remaining_listening_minutes`, `started_at`, `expires_at`) VALUES
  (1, 1, '已开通', 1200, '2026-04-01 09:00:00', '2027-04-01 09:00:00'),
  (2, 2, '未开通',   30, '2026-04-02 10:30:00', '2026-05-02 10:30:00'),
  (3, 3, '已开通', 3000, '2026-04-03 19:20:00', '2027-04-03 19:20:00');

INSERT INTO `coupons` (`id`, `coupon_code`, `coupon_info`, `discount_type`, `discount_value`, `status`, `expires_at`) VALUES
  (1, 'VIP50OFF',  'VIP会员月卡 5 折优惠券',        '折扣',   0.50, '未使用', '2026-12-31 23:59:59'),
  (2, 'BOOK20',    '全场听书满 20 减 5 元优惠券',   '满减',   5.00, '未使用', '2026-12-31 23:59:59'),
  (3, 'NEWUSER10', '新用户专享 10 元无门槛优惠券',  '无门槛', 10.00, '未使用', '2026-12-31 23:59:59'),
  (4, 'VIPMONTH',  'VIP会员月卡兑换码',             '兑换',   0.00, '已使用', '2026-12-31 23:59:59');

INSERT INTO `coupon_redemptions` (`id`, `redemption_id`, `coupon_id`, `user_id`, `operator`, `status`, `status_desc`, `created_at`) VALUES
  (1, 'CR202604100001', 1, 1, 'system', 'success',   '优惠码兑换成功，VIP会员月卡5折优惠已到账。', '2026-04-10 18:00:00'),
  (2, 'CR202604060002', 4, 3, 'system', 'success',   '兑换成功，VIP会员月卡已生效。',              '2026-04-06 12:40:00'),
  (3, 'CR202604110003', 2, 2, 'system', 'submitted', '优惠码已提交，正在处理中。',                '2026-04-11 10:20:00');

INSERT INTO `chapters` (`id`, `book_id`, `chapter_number`, `title`, `duration_minutes`) VALUES
  (1, 1, 1, '科学边界',     40),
  (2, 1, 2, '台球',         45),
  (3, 1, 3, '射手和农场主', 42),
  (4, 2, 1, '朱元璋的崛起', 30),
  (5, 2, 2, '洪武大帝',     32),
  (6, 3, 1, '少年福贵',     28),
  (7, 3, 2, '家道中落',     30),
  (8, 4, 1, '黄土高原',     30),
  (9, 4, 2, '少平与少安',   33);

INSERT INTO `refund_requests` (`id`, `refund_id`, `order_id`, `operator`, `reason`, `status`, `status_desc`, `created_at`) VALUES
  (1, 'R202604070001', 3, 'system', '误购了听书，希望退款',       'completed',  '退款已完成，款项已原路退回。', '2026-04-07 09:30:00'),
  (2, 'R202604100002', 7, 'system', '重复购买了同一本听书',       'processing', '退款申请正在审核中。',         '2026-04-10 16:20:00');