# 食材清单审阅与索引重建

可执行入口：`python3 scripts/recipe-ingredients.py`，仅使用Python标准库，无需SQLite、模型服务或系统switch。规则见[食材契约](../specs/010-host-configuration/contracts/video-recipe-ingredients.md)。

## 一轮操作

在nix-tools仓库运行，`RECIPE_LIB`替换为实际菜谱库目录。这里的文件名是示例；每次选择新版本名称，工具拒绝覆盖已有文件。

```bash
RECIPE_LIB='/home/liou/Downloads/Bilibili/老东北美食 [514273130]/菜谱库试验-10道'
python3 scripts/recipe-ingredients.py collect \
  --input "$RECIPE_LIB/recipes" --output /tmp/ingredient-inventory.json
python3 scripts/recipe-ingredients.py prepare-review \
  --input /tmp/ingredient-inventory.json --output /tmp/ingredient-review-input.json
```

将review-input与契约/审阅Schema交给AI，保存输出为`/tmp/ingredient-review.json`。缺证据的项目按occurrence_id从完整inventory取回更多上下文。模型访问当前由交互式会话承担；这些命令不会自行调用AI。也可collect现有search-index.json，但索引没有原文时不能声称上下文已核对。

```bash
python3 scripts/recipe-ingredients.py apply \
  --inventory /tmp/ingredient-inventory.json --review /tmp/ingredient-review.json \
  --output /tmp/ingredients-next.json
python3 scripts/recipe-ingredients.py reindex \
  --input "$RECIPE_LIB/search-index.json" --dictionary /tmp/ingredients-next.json \
  --output "$RECIPE_LIB/search-index-v2.json"
python3 scripts/recipe-ingredients.py directory \
  --input "$RECIPE_LIB/search-index-v2.json" --dictionary /tmp/ingredients-next.json \
  --output "$RECIPE_LIB/index-v2.html"
```

directory生成固定模板的离线目录并内嵌新索引，没有fetch/file跨域依赖。输出HTML须与输入索引同目录，引用的相对菜谱/缩略图文件必须真实存在且位于库内；仅在有完整菜谱库时才能生成，不能用食材数据冒充已完成菜谱。搜索多词默认AND，允许关闭可选配料，每页24项。

核验新目录后，用明确新版本更新`config/recipe/ingredients.json`作为后续权威词典，并提交；历史review/inventory放在菜谱库，不进入远端资料镜像。程序apply只生成新文件，不直接覆盖权威词典。词典更新只重建检索，不改视频、字幕、用量、配方或旧页面。修改后必须同时更新页面内嵌索引，不能仅替换外部JSON。

## 当前试验范围

首轮是当前十个视频的AI试稿食材清单：76个不同名称，70个名称映射到60个食材身份，3个上位大类，6个名称保留歧义。这不代表十份完整图文菜谱或独立后台AI流水线已经交付，也不是人工食材校对。

阶段名称如压制/收汁归同一身份，但原名与两次用量仍分开；蘑菇品种不相互合并；小葱绿保留为叶部。明油、汤水、水或清汤、老抽或红烧王酱油、大料及未明确组成的香料暂不自动扩展。当前词典面向这一资料库；应用于其他作者或方言来源时重新汇总审阅，不把本次来源中的用语直接视为跨地区通用结论。

本地回归：

```bash
python3 -m unittest discover -s scripts/tests -p test_recipe_ingredients.py -v
node --test scripts/tests/test_recipe_ingredient_search.cjs
```
