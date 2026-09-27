# datapod (dp)

A fast, metadata-rich, content-addressable data vault and pod manager for the terminal.

Store files, models, datasets, configs, and logs with metadata, ownership tags, and timestamps — then access them instantly using unique compact pod IDs.

---

## ⚡ Your Workflow

### 1. Store a file with metadata & holder
```bash
datapod -add dataset.csv -meta 'dataset.csv | snehil'
# or using key=value pairs:
datapod -add model.onnx -meta 'holder=analytics,version=2.1,env=prod'
```

Output:
```text
╭───────────────────────────────────────────────────╮
│  POD STORED SUCCESSFULLY                          │
├───────────────────────────────────────────────────┤
│ ID       : 47cbb0b5                               │
│ File     : dataset.csv                            │
│ Holder   : snehil                                 │
│ Size     : 24 B (24 bytes)                        │
│ Timestamp: 2026-09-27T22:39:15+05:30              │
│ SHA-256  : 7ae7d392f5f6b382...                    │
├───────────────────────────────────────────────────┤
│ Metadata:                                         │
│  • label: dataset.csv                             │
╰───────────────────────────────────────────────────╯

Access with: datapod -pull 47cbb0b5
```

---

### 2. Pull / Retrieve any file with its unique ID
```bash
datapod -pull 47cbb0b5
# or specify destination output file:
datapod -pull 47cbb0b5 -out ./restored_data.csv
```

---

### 3. Inspect Pod Metadata & Checksums
```bash
datapod -info 47cbb0b5
```

---

### 4. Stream or Pipe File Content (`-cat`)
```bash
datapod -cat 47cbb0b5 | grep "error"
```

---

### 5. List Vault Entries
```bash
datapod -list
# or filter by holder:
datapod -list -holder snehil
```
```text
ID         HOLDER         FILE                   SIZE       TIMESTAMP           
────────────────────────────────────────────────────────────────────────────────
47cbb0b5   snehil         dataset.csv            24 B       2026-09-27 22:39    
de883921   dev_ops        sample.log             18 B       2026-09-27 22:38    
```

---

## 🚀 Key Architectural Highlights

1. **Content-Addressable Storage (CAS)**:
   - Data blobs are stored by their SHA-256 hash. If you store two identical 500MB files, they are automatically **deduplicated** and take up storage only once.
2. **Atomic Disk Writes**:
   - Uses temporary file swaps to prevent data corruption during mid-write system interruptions.
3. **Local or Global Repositories**:
   - Runs in global mode (`~/.datapod`) by default, or run `datapod init` inside any project folder to create a project-local `.datapod/` vault.
4. **Zero Dependencies**:
   - Pure Python standard library. Runs in under 15ms.

---

## 📦 Installation

```bash
git clone https://github.com/khokharsnehil45/datapod.git
cd datapod
pip install -e .
```

Installs both `datapod` and the quick alias `dp`.
