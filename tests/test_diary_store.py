"""DiaryStore 单元测试。"""
import json
import os
import threading


def test_save_diary_creates_file_and_index(fresh_diary_store, fake_emotion):
    store = fresh_diary_store
    diary_id = store.save_diary("今天散步很开心", "日记正文内容较长..." + "x" * 100, fake_emotion)

    assert diary_id  # 非空
    # 文件存在
    diary_file = os.path.join(store.diary_dir, f"{diary_id}.json")
    assert os.path.exists(diary_file)
    with open(diary_file, "r", encoding="utf-8") as f:
        entry = json.load(f)
    assert entry["user_input"] == "今天散步很开心"
    assert entry["emotion"] == "开心"
    assert entry["intensity"] == 8

    # 索引含一条记录
    index = store.get_all_diaries()
    assert len(index) == 1
    assert index[0]["id"] == diary_id
    assert index[0]["emotion"] == "开心"


def test_save_multiple_diaries_inserts_at_head(fresh_diary_store, fake_emotion):
    store = fresh_diary_store
    id1 = store.save_diary("第一条", "内容1", fake_emotion)
    id2 = store.save_diary("第二条", "内容2", fake_emotion)
    index = store.get_all_diaries()
    assert len(index) == 2
    # 新的排在前面
    assert index[0]["id"] == id2
    assert index[1]["id"] == id1


def test_get_diary_returns_none_if_not_exist(fresh_diary_store):
    assert fresh_diary_store.get_diary("nonexistent_id") is None


def test_get_diary_returns_entry(fresh_diary_store, fake_emotion):
    store = fresh_diary_store
    did = store.save_diary("用户输入", "日记正文", fake_emotion)
    entry = store.get_diary(did)
    assert entry is not None
    assert entry["id"] == did
    assert entry["diary"] == "日记正文"


def test_delete_diary(fresh_diary_store, fake_emotion):
    store = fresh_diary_store
    did = store.save_diary("待删除", "内容", fake_emotion)
    assert store.delete_diary(did) is True
    # 删除后查不到
    assert store.get_diary(did) is None
    # 索引同步更新
    assert len(store.get_all_diaries()) == 0
    # 重复删除返回 False
    assert store.delete_diary(did) is False


def test_search_diaries_matches_keyword(fresh_diary_store, fake_emotion):
    store = fresh_diary_store
    store.save_diary("今天去公园散步", "阳光明媚，公园里花都开了", fake_emotion)
    sad_emotion = {"emotion": "悲伤", "intensity": 3, "keywords": [], "brief_analysis": ""}
    store.save_diary("工作不顺心", "今天被领导批评了，心情低落", sad_emotion)

    # 关键词命中预览文本
    results = store.search_diaries("公园")
    assert len(results) == 1
    assert results[0]["emotion"] == "开心"

    # 关键词命中情绪字段
    results = store.search_diaries("悲伤")
    assert len(results) == 1

    # 空关键词返回空列表
    assert store.search_diaries("") == []


def test_search_diaries_case_insensitive(fresh_diary_store, fake_emotion):
    store = fresh_diary_store
    store.save_diary("hello world", "Hello World", fake_emotion)
    results = store.search_diaries("HELLO")
    assert len(results) == 1


def test_export_markdown_format(fresh_diary_store, fake_emotion):
    store = fresh_diary_store
    did = store.save_diary("今天心情不错", "日记正文内容", fake_emotion)
    md = store.export_markdown(did)
    assert "# 📔 心语日记" in md
    assert "情绪：开心" in md
    assert "强度：8/10" in md
    assert "日记正文内容" in md


def test_export_markdown_nonexistent_returns_empty(fresh_diary_store):
    assert fresh_diary_store.export_markdown("nonexistent") == ""


def test_export_all_markdown_empty(fresh_diary_store):
    md = fresh_diary_store.export_all_markdown()
    assert "暂无日记" in md


def test_export_all_markdown_contains_all(fresh_diary_store, fake_emotion):
    store = fresh_diary_store
    store.save_diary("第一条", "内容1", fake_emotion)
    store.save_diary("第二条", "内容2", fake_emotion)
    md = store.export_all_markdown()
    assert "内容1" in md
    assert "内容2" in md


def test_thread_safety_concurrent_writes(fresh_diary_store, fake_emotion):
    """并发写入 20 条日记，不应出现索引损坏。"""
    store = fresh_diary_store
    errors = []

    def worker(i):
        try:
            store.save_diary(f"并发输入{i}", f"内容{i}", fake_emotion)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"并发写入出现错误: {errors}"
    assert len(store.get_all_diaries()) == 20
