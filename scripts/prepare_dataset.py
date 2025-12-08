#!/usr/bin/env python3
"""
データセット準備スクリプト
- YOLO形式のアノテーションと画像をtrain/valに分割
- 学習用ディレクトリ構造を作成
"""

import os
import shutil
import random
from pathlib import Path

# 設定
IMAGES_DIR = Path("training_data/soccer_ball")
ANNOTATIONS_DIR = Path("training_data/annotations")
OUTPUT_DIR = Path("training_data/dataset")
TRAIN_RATIO = 0.8  # 80%を訓練用、20%を検証用

def prepare_dataset():
    """データセットを訓練/検証用に分割"""

    print("=== データセット準備開始 ===")

    # 1. ディレクトリ確認
    if not IMAGES_DIR.exists():
        print(f"エラー: 画像ディレクトリが見つかりません: {IMAGES_DIR}")
        return False

    if not ANNOTATIONS_DIR.exists():
        print(f"エラー: アノテーションディレクトリが見つかりません: {ANNOTATIONS_DIR}")
        return False

    # 2. 画像とアノテーションのペアを取得
    image_files = list(IMAGES_DIR.glob("*.jpg")) + list(IMAGES_DIR.glob("*.png"))
    print(f"画像数: {len(image_files)}枚")

    # アノテーションファイルの存在を確認
    valid_pairs = []
    for img_path in image_files:
        ann_path = ANNOTATIONS_DIR / (img_path.stem + ".txt")
        if ann_path.exists():
            valid_pairs.append((img_path, ann_path))
        else:
            print(f"警告: アノテーションなし: {img_path.name}")

    print(f"有効なペア数: {len(valid_pairs)}")

    if len(valid_pairs) == 0:
        print("エラー: 有効な画像-アノテーションペアが見つかりません")
        return False

    # 3. ランダムシャッフル
    random.seed(42)  # 再現性のため
    random.shuffle(valid_pairs)

    # 4. 訓練/検証に分割
    split_idx = int(len(valid_pairs) * TRAIN_RATIO)
    train_pairs = valid_pairs[:split_idx]
    val_pairs = valid_pairs[split_idx:]

    print(f"訓練データ: {len(train_pairs)}枚")
    print(f"検証データ: {len(val_pairs)}枚")

    # 5. ディレクトリ構造作成
    dirs_to_create = [
        OUTPUT_DIR / "train" / "images",
        OUTPUT_DIR / "train" / "labels",
        OUTPUT_DIR / "val" / "images",
        OUTPUT_DIR / "val" / "labels",
    ]

    for dir_path in dirs_to_create:
        dir_path.mkdir(parents=True, exist_ok=True)

    # 6. ファイルをコピー
    print("\n訓練データをコピー中...")
    for img_path, ann_path in train_pairs:
        shutil.copy2(img_path, OUTPUT_DIR / "train" / "images" / img_path.name)
        shutil.copy2(ann_path, OUTPUT_DIR / "train" / "labels" / ann_path.name)

    print("検証データをコピー中...")
    for img_path, ann_path in val_pairs:
        shutil.copy2(img_path, OUTPUT_DIR / "val" / "images" / img_path.name)
        shutil.copy2(ann_path, OUTPUT_DIR / "val" / "labels" / ann_path.name)

    # 7. data.yamlファイルを作成（YOLO学習用設定）
    yaml_content = f"""# Soccer Ball Dataset Configuration
path: {OUTPUT_DIR.absolute()}
train: train/images
val: val/images

# Classes
nc: 1  # number of classes
names: ['soccer_ball']  # class names
"""

    yaml_path = OUTPUT_DIR / "data.yaml"
    with open(yaml_path, 'w') as f:
        f.write(yaml_content)

    print(f"\ndata.yaml作成完了: {yaml_path}")

    # 8. 統計表示
    print("\n=== データセット準備完了 ===")
    print(f"出力ディレクトリ: {OUTPUT_DIR.absolute()}")
    print(f"訓練データ: {len(train_pairs)}枚 ({TRAIN_RATIO*100:.0f}%)")
    print(f"検証データ: {len(val_pairs)}枚 ({(1-TRAIN_RATIO)*100:.0f}%)")
    print(f"\n次のステップ: Google Colabで学習を実行してください")

    return True


if __name__ == "__main__":
    success = prepare_dataset()
    exit(0 if success else 1)
