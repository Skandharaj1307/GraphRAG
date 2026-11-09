import numpy as np
for f in ["defect_embeddings.npy", "screenshot_embeddings.npy", "testcase_embeddings.npy"]:
    a = np.load(f, mmap_mode="r")
    print(f, a.shape, a.dtype)