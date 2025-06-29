# Veri-Madenciligi
HepsiEmlak sitesinden çekilen veriler üzerinde önişleme adımları (veri ekleme, silme, dönüştürme, eksik değerleri doldurma ve veri setlerini birleştirme) gerçekleştirildikten sonra, elde edilen temiz veri seti üzerinde ev fiyatı (price) sütununu hedef değişken olarak alarak çeşitli makine öğrenmesi algoritmaları uygulanmıştır.

Bu kapsamda; Linear Regression, Logistic Regression, K-Nearest Neighbors (KNN), K-Means, Apriori, Decision Tree, Naive Bayes, CatBoost ve XGBoost olmak üzere toplam 9 farklı algoritma ile ev fiyat tahmini yapılmıştır. Her bir modelin performansı değerlendirilerek en uygun tahminleme algoritmasını belirlemek hedeflenmiştir.

Modelleme sürecinde; feature engineering, logaritmik dönüşümler, VIF (Variance Inflation Factor) analizi ile çoklu doğrusal bağlantıların kontrolü sağlanmış, modellerin doğruluğunu ve genellenebilirliğini artırmak amacıyla çeşitli optimizasyon teknikleri kullanılmıştır. Bu kapsamda, hiperparametre ayarlamaları için Grid Search ve Random Search yöntemlerinden yararlanılmış; ayrıca model geçerliliğini değerlendirmek üzere Cross-Validation (çapraz doğrulama) uygulanmıştır.
