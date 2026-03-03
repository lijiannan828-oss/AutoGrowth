# 数据库规则 (Firestore)

## 服务层规范

```typescript
// src/lib/firebase/personal-assets.ts
import { db } from './config';
import {
  collection, doc, getDocs, addDoc, updateDoc, deleteDoc,
  query, where, serverTimestamp, Timestamp
} from 'firebase/firestore';

// 定义类型
export interface PersonalAsset {
  id: string;
  userId: string;
  name: string;
  type: 'image' | 'video' | 'prompt';
  createdAt: string | Timestamp;
}

const COLLECTION_NAME = 'personal_assets';

// 获取数据
export async function getPersonalAssets(userId: string): Promise<PersonalAsset[]> {
  try {
    const q = query(
      collection(db, COLLECTION_NAME),
      where('userId', '==', userId)
    );
    const snapshot = await getDocs(q);
    return snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() })) as PersonalAsset[];
  } catch (error) {
    console.error('❌ 获取数据失败:', error);
    return [];
  }
}

// 添加数据 - 过滤 undefined 值
export async function addPersonalAsset(asset: Omit<PersonalAsset, 'id'>): Promise<string> {
  // 🔥 Firestore 不支持 undefined，必须过滤
  const cleanedAsset: any = {};
  Object.entries(asset).forEach(([key, value]) => {
    if (value !== undefined) {
      cleanedAsset[key] = value;
    }
  });

  const docRef = await addDoc(collection(db, COLLECTION_NAME), {
    ...cleanedAsset,
    createdAt: serverTimestamp(),
  });
  return docRef.id;
}
```
