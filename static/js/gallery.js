/**
 * ComfyUI 自动化系统 - 图片画廊交互逻辑
 * 功能：图片展示、筛选、选择、评分、收藏等交互功能
 */

class GalleryManager {
    constructor() {
        this.images = [];
        this.filteredImages = [];
        this.selectedImages = new Set();
        this.favorites = new Set();
        this.userTags = new Map(); // imageId -> tags array
        this.userRatings = new Map(); // imageId -> rating number
        this.popularTags = ['高质量', '人像', '风景', '动漫', '写实', '艺术'];
        this.currentView = 'grid';
        this.currentSort = 'date_desc';
        this.selectionMode = false;
        this.currentModalImageId = null;
        this.currentFilters = {
            search: '',
            dateFrom: '',
            dateTo: '',
            status: ['completed'],
            qualityMin: 0,
            tags: [],
            favoritesOnly: false
        };
        
        this.init();
    }

    /**
     * 初始化画廊管理器
     */
    init() {
        this.loadUserPreferences();
        this.bindEvents();
        this.loadImages();
        this.updateDisplay();
    }

    /**
     * 绑定事件监听器
     */
    bindEvents() {
        // 搜索功能
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.currentFilters.search = e.target.value;
                this.applyFilters();
            });
        }

        // 日期筛选
        const dateFrom = document.getElementById('dateFrom');
        const dateTo = document.getElementById('dateTo');
        if (dateFrom) {
            dateFrom.addEventListener('change', (e) => {
                this.currentFilters.dateFrom = e.target.value;
                this.applyFilters();
            });
        }
        if (dateTo) {
            dateTo.addEventListener('change', (e) => {
                this.currentFilters.dateTo = e.target.value;
                this.applyFilters();
            });
        }

        // 状态筛选
        const statusCheckboxes = document.querySelectorAll('input[type="checkbox"][value]');
        statusCheckboxes.forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                const value = e.target.value;
                if (e.target.checked) {
                    this.currentFilters.status.push(value);
                } else {
                    this.currentFilters.status = this.currentFilters.status.filter(s => s !== value);
                }
                this.applyFilters();
            });
        });

        // 质量评分筛选
        const qualityRange = document.getElementById('qualityRange');
        if (qualityRange) {
            qualityRange.addEventListener('input', (e) => {
                this.currentFilters.qualityMin = parseFloat(e.target.value);
                document.getElementById('qualityValue').textContent = e.target.value;
                this.applyFilters();
            });
        }

        // 排序功能
        const sortSelect = document.getElementById('sortBy');
        if (sortSelect) {
            sortSelect.addEventListener('change', (e) => {
                this.currentSort = e.target.value;
                this.applySorting();
            });
        }

        // 视图切换
        const viewButtons = document.querySelectorAll('.view-btn');
        viewButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.switchView(e.target.dataset.view);
            });
        });

        // 图片大小控制
        const sizeSlider = document.getElementById('imageSizeSlider');
        if (sizeSlider) {
            sizeSlider.addEventListener('input', (e) => {
                this.updateImageSize(parseInt(e.target.value));
            });
        }

        // 批量操作按钮
        this.bindBatchActions();
        
        // 模态框相关
        this.bindModalEvents();
        
        // 全局事件
        this.bindGlobalEvents();

        // 导入文件夹
        this.bindImportFolder();
    }

    /**
     * 绑定全局事件
     */
    bindGlobalEvents() {
        // 点击其他地方关闭下拉菜单
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.export-dropdown')) {
                document.querySelectorAll('.dropdown-menu').forEach(menu => {
                    menu.classList.remove('show');
                });
            }
        });
    }

    /**
     * 绑定批量操作事件
     */
    bindBatchActions() {
        // 多选模式切换
        const selectionModeBtn = document.getElementById('selectionModeBtn');
        if (selectionModeBtn) {
            selectionModeBtn.addEventListener('click', () => {
                this.toggleSelectionMode();
            });
        }

        // 全选/反选/清空选择
        const selectAllBtn = document.getElementById('selectAllBtn');
        const invertSelectionBtn = document.getElementById('invertSelectionBtn');
        const clearSelectionBtn = document.getElementById('clearSelectionBtn');
        
        if (selectAllBtn) {
            selectAllBtn.addEventListener('click', () => {
                this.selectAllVisible();
            });
        }
        
        if (invertSelectionBtn) {
            invertSelectionBtn.addEventListener('click', () => {
                this.invertSelection();
            });
        }
        
        if (clearSelectionBtn) {
            clearSelectionBtn.addEventListener('click', () => {
                this.clearSelection();
            });
        }

        // 导出选中
        const exportBtn = document.getElementById('exportSelectedBtn');
        if (exportBtn) {
            exportBtn.addEventListener('click', () => {
                this.exportSelected('json');
            });
        }

        // 导出下拉菜单
        const exportDropdownBtn = document.getElementById('exportDropdownBtn');
        if (exportDropdownBtn) {
            exportDropdownBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleDropdown('exportDropdownMenu');
            });
        }

        // 批量标签
        const addBatchTagBtn = document.getElementById('addBatchTagBtn');
        const batchTagInput = document.getElementById('batchTagInput');
        
        if (addBatchTagBtn) {
            addBatchTagBtn.addEventListener('click', () => {
                this.addBatchTag();
            });
        }
        
        if (batchTagInput) {
            batchTagInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.addBatchTag();
                }
            });
        }

        // 删除选中
        const deleteBtn = document.getElementById('deleteSelectedBtn');
        if (deleteBtn) {
            deleteBtn.addEventListener('click', () => {
                this.deleteSelected();
            });
        }

        // 显示收藏
        const showFavoritesBtn = document.getElementById('showFavoritesBtn');
        if (showFavoritesBtn) {
            showFavoritesBtn.addEventListener('click', () => {
                this.toggleFavoritesOnly();
            });
        }
    }

    /**
     * 绑定“导入文件夹”事件
     */
    bindImportFolder() {
        const importBtn = document.getElementById('importFolderBtn');
        const singleFolderInput = document.getElementById('folderInput');
        const multiFolderInput = document.getElementById('multiFolderInput');
        const singleFolderItem = document.getElementById('importSingleFolder');
        const multiFolderItem = document.getElementById('importMultiFolder');
        
        if (!importBtn || !singleFolderInput || !multiFolderInput) return;

        // 单个文件夹选择
        if (singleFolderItem) {
            singleFolderItem.addEventListener('click', (e) => {
                e.preventDefault();
                singleFolderInput.value = '';
                singleFolderInput.click();
            });
        }

        // 多个文件夹选择
        if (multiFolderItem) {
            multiFolderItem.addEventListener('click', (e) => {
                e.preventDefault();
                multiFolderInput.value = '';
                multiFolderInput.click();
            });
        }

        // 处理单个文件夹导入
        singleFolderInput.addEventListener('change', (e) => {
            const files = Array.from(e.target.files || []);
            if (!files.length) return;
            this.importFromDirectory(files, 'single');
        });

        // 处理多个文件夹导入
        multiFolderInput.addEventListener('change', (e) => {
            const files = Array.from(e.target.files || []);
            if (!files.length) return;
            this.importFromDirectory(files, 'multi');
        });
    }

    /**
     * 从目录导入图片文件
     */
    importFromDirectory(files, mode = 'single') {
        // 基础过滤：只接收图片类型
        const imageFiles = files.filter(f => f.type && f.type.startsWith('image/'));
        if (imageFiles.length === 0) {
            this.showToast('未在该文件夹中发现图片文件', 'warning');
            return;
        }

        // 按文件夹分组（多选模式）
        const folderGroups = {};
        if (mode === 'multi') {
            imageFiles.forEach(file => {
                const pathParts = file.webkitRelativePath.split('/');
                const folderName = pathParts[0] || '未知文件夹';
                if (!folderGroups[folderName]) {
                    folderGroups[folderName] = [];
                }
                folderGroups[folderName].push(file);
            });
        } else {
            // 单选模式，所有文件归为一个组
            folderGroups['导入文件夹'] = imageFiles;
        }

        const importedIds = [];
        let totalImported = 0;

        Object.entries(folderGroups).forEach(([folderName, folderFiles]) => {
            folderFiles.forEach((file, idx) => {
                const id = `local_${Date.now()}_${totalImported}_${Math.random().toString(36).slice(2,8)}`;
                const objectUrl = URL.createObjectURL(file);
                const createdAt = new Date(file.lastModified || Date.now()).toISOString();
                const fileSizeMb = file.size ? (file.size / (1024 * 1024)) : 0;

                const entry = {
                    id,
                    taskId: id,
                    filename: file.name,
                    src: objectUrl,
                    prompt: file.name,
                    createdAt,
                    generationTime: 0,
                    qualityScore: 0.5,
                    fileSize: parseFloat(fileSizeMb.toFixed(2)),
                    resolution: '未知',
                    status: 'completed',
                    tags: [],
                    workflowParams: {},
                    folderName: folderName  // 添加文件夹信息
                };

                this.images.unshift(entry);
                importedIds.push(id);
                totalImported++;

                // 异步读取尺寸信息
                try {
                    const img = new Image();
                    img.onload = () => {
                        entry.resolution = `${img.naturalWidth}x${img.naturalHeight}`;
                        // 局部刷新：不必全量重渲染，影响不大时可忽略
                    };
                    img.src = objectUrl;
                } catch (_) {}
            });
        });

        this.filteredImages = [...this.images];
        this.applySorting();
        this.updateDisplay();

        // 自动选中本次导入的图片，便于批量操作
        importedIds.forEach(id => this.selectedImages.add(id));
        this.updateSelectionDisplay();

        // 显示导入结果
        const folderCount = Object.keys(folderGroups).length;
        const message = mode === 'multi' 
            ? `成功导入 ${totalImported} 张图片，来自 ${folderCount} 个文件夹`
            : `成功导入 ${totalImported} 张图片`;
        this.showToast(message, 'success');
    }

    /**
     * 绑定模态框事件
     */
    bindModalEvents() {
        const modal = document.getElementById('imageModal');
        const modalClose = document.getElementById('modalClose');
        const modalBackdrop = document.getElementById('modalBackdrop');

        if (modalClose) {
            modalClose.addEventListener('click', () => {
                this.closeModal();
            });
        }

        if (modalBackdrop) {
            modalBackdrop.addEventListener('click', () => {
                this.closeModal();
            });
        }

        // 星级评分
        const starRating = document.getElementById('starRating');
        if (starRating) {
            starRating.addEventListener('click', (e) => {
                if (e.target.classList.contains('fa-star')) {
                    const rating = parseInt(e.target.dataset.rating);
                    this.rateImage(this.currentModalImageId, rating);
                }
            });
        }

        // 标签添加
        const addTagBtn = document.getElementById('addTagBtn');
        const tagInput = document.getElementById('tagInput');
        
        if (addTagBtn) {
            addTagBtn.addEventListener('click', () => {
                this.addTagToCurrentImage();
            });
        }
        
        if (tagInput) {
            tagInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.addTagToCurrentImage();
                }
            });
        }

        // 收藏切换
        const toggleFavoriteBtn = document.getElementById('toggleFavoriteBtn');
        if (toggleFavoriteBtn) {
            toggleFavoriteBtn.addEventListener('click', () => {
                this.toggleFavorite(this.currentModalImageId);
            });
        }

        // 下载按钮
        const downloadBtn = document.getElementById('downloadBtn');
        if (downloadBtn) {
            downloadBtn.addEventListener('click', () => {
                this.downloadImage(this.currentModalImageId);
            });
        }

        // 复制提示词
        const copyPromptBtn = document.getElementById('copyPromptBtn');
        if (copyPromptBtn) {
            copyPromptBtn.addEventListener('click', () => {
                this.copyPrompt(this.currentModalImageId);
            });
        }
    }

    /**
     * 加载图片数据
     */
    async loadImages() {
        try {
            this.showLoading(true);
            
            // 模拟API调用 - 实际项目中应该从后端获取数据
            const response = await fetch('/api/images');
            if (response.ok) {
                this.images = await response.json();
            } else {
                // 如果API不可用，使用模拟数据
                this.images = this.generateMockData();
            }
            
            this.filteredImages = [...this.images];
            this.applySorting();
            this.updateDisplay();
            
        } catch (error) {
            console.error('加载图片数据失败:', error);
            // 使用模拟数据作为后备
            this.images = this.generateMockData();
            this.filteredImages = [...this.images];
            this.applySorting();
            this.updateDisplay();
        } finally {
            this.showLoading(false);
        }
    }

    /**
     * 生成模拟数据（用于测试）
     */
    generateMockData() {
        const mockImages = [];
        const prompts = [
            'A beautiful landscape with mountains and lakes',
            'Portrait of a young woman in vintage clothing',
            'Futuristic cityscape at sunset',
            'Abstract art with vibrant colors',
            'Cute cat sitting on a windowsill',
            'Steampunk mechanical device',
            'Fantasy castle in the clouds',
            'Minimalist geometric design'
        ];

        for (let i = 1; i <= 20; i++) {
            mockImages.push({
                id: `img_${i}`,
                taskId: `task_${i}`,
                filename: `image_${i}.png`,
                prompt: prompts[Math.floor(Math.random() * prompts.length)],
                createdAt: new Date(Date.now() - Math.random() * 7 * 24 * 60 * 60 * 1000).toISOString(),
                generationTime: Math.random() * 30 + 5,
                qualityScore: Math.random(),
                fileSize: Math.random() * 5 + 1,
                resolution: '512x512',
                status: Math.random() > 0.1 ? 'completed' : 'failed',
                tags: ['art', 'digital', 'creative'].slice(0, Math.floor(Math.random() * 3) + 1),
                workflowParams: {
                    steps: Math.floor(Math.random() * 20) + 10,
                    cfg: 7.5,
                    seed: Math.floor(Math.random() * 1000000)
                }
            });
        }

        return mockImages;
    }

    /**
     * 应用筛选条件
     */
    applyFilters() {
        this.filteredImages = this.images.filter(image => {
            // 搜索筛选
            if (this.currentFilters.search) {
                const searchTerm = this.currentFilters.search.toLowerCase();
                if (!image.prompt.toLowerCase().includes(searchTerm) &&
                    !image.tags.some(tag => tag.toLowerCase().includes(searchTerm))) {
                    return false;
                }
            }

            // 日期筛选
            if (this.currentFilters.dateFrom) {
                const imageDate = new Date(image.createdAt);
                const fromDate = new Date(this.currentFilters.dateFrom);
                if (imageDate < fromDate) return false;
            }
            if (this.currentFilters.dateTo) {
                const imageDate = new Date(image.createdAt);
                const toDate = new Date(this.currentFilters.dateTo);
                if (imageDate > toDate) return false;
            }

            // 状态筛选
            if (!this.currentFilters.status.includes(image.status)) {
                return false;
            }

            // 质量筛选
            if (image.qualityScore < this.currentFilters.qualityMin) {
                return false;
            }

            // 标签筛选
            if (this.currentFilters.tags.length > 0) {
                if (!this.currentFilters.tags.some(tag => image.tags.includes(tag))) {
                    return false;
                }
            }

            // 收藏筛选
            if (this.currentFilters.favoritesOnly && !this.favorites.has(image.id)) {
                return false;
            }

            return true;
        });

        this.applySorting();
        this.updateDisplay();
    }

    /**
     * 应用排序
     */
    applySorting() {
        this.filteredImages.sort((a, b) => {
            switch (this.currentSort) {
                case 'date_desc':
                    return new Date(b.createdAt) - new Date(a.createdAt);
                case 'date_asc':
                    return new Date(a.createdAt) - new Date(b.createdAt);
                case 'quality_desc':
                    return b.qualityScore - a.qualityScore;
                case 'quality_asc':
                    return a.qualityScore - b.qualityScore;
                case 'name_asc':
                    return a.filename.localeCompare(b.filename);
                case 'name_desc':
                    return b.filename.localeCompare(a.filename);
                default:
                    return 0;
            }
        });
    }

    /**
     * 更新显示
     */
    updateDisplay() {
        this.renderImages();
        this.updateStats();
        this.updateTags();
    }

    /**
     * 渲染图片网格
     */
    renderImages() {
        const galleryGrid = document.getElementById('galleryGrid');
        if (!galleryGrid) return;

        galleryGrid.innerHTML = '';

        if (this.filteredImages.length === 0) {
            this.showNoResults(true);
            return;
        }

        this.showNoResults(false);

        this.filteredImages.forEach(image => {
            const imageCard = this.createImageCard(image);
            galleryGrid.appendChild(imageCard);
        });

        // 更新显示计数
        const displayedCount = document.getElementById('displayedCount');
        const totalCount = document.getElementById('totalCount');
        if (displayedCount) displayedCount.textContent = this.filteredImages.length;
        if (totalCount) totalCount.textContent = this.images.length;
    }

    /**
     * 创建图片卡片
     */
    createImageCard(image) {
        const card = document.createElement('div');
        card.className = 'image-card';
        card.dataset.imageId = image.id;

        if (this.selectedImages.has(image.id)) {
            card.classList.add('selected');
        }

        const qualityClass = this.getQualityClass(image.qualityScore);
        const isFavorite = this.favorites.has(image.id);

        const previewSrc = image.src || `/api/image/${image.filename}`;
        card.innerHTML = `
            <div class="selection-checkbox">
                <i class="fas fa-check"></i>
            </div>
            <div class="image-preview" onclick="galleryManager.openModal('${image.id}')">
                <img src="${previewSrc}" alt="${image.prompt}" 
                     onerror="this.src='data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjUwIiBoZWlnaHQ9IjI1MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZjBmMGYwIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxNCIgZmlsbD0iIzk5OTk5OSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPkltYWdlPC90ZXh0Pjwvc3ZnPg=='">
                <div class="image-quality-badge ${qualityClass}">
                    ${(image.qualityScore * 100).toFixed(0)}%
                </div>
                <div class="image-actions">
                    <button class="action-btn favorite ${isFavorite ? 'active' : ''}" 
                            onclick="event.stopPropagation(); galleryManager.toggleFavorite('${image.id}')">
                        <i class="fas fa-heart"></i>
                    </button>
                    <button class="action-btn" onclick="event.stopPropagation(); galleryManager.openModal('${image.id}')">
                        <i class="fas fa-expand"></i>
                    </button>
                </div>
            </div>
            <div class="image-info">
                <div class="image-title">${image.filename}</div>
                <div class="image-prompt">${image.prompt}</div>
                <div class="image-meta">
                    <span class="meta-item">${new Date(image.createdAt).toLocaleDateString()}</span>
                    <span class="meta-item">${image.generationTime.toFixed(1)}s</span>
                </div>
                <div class="image-tags">
                    ${image.tags.map(tag => `<span class="tag">${tag}</span>`).join('')}
                </div>
            </div>
        `;

        // 添加选择事件
        card.addEventListener('click', (e) => {
            if (!e.target.closest('.image-actions') && 
                (!e.target.closest('.image-preview') || e.target.closest('.selection-checkbox'))) {
                this.toggleSelection(image.id);
            }
        });

        return card;
    }

    /**
     * 获取质量等级类名
     */
    getQualityClass(score) {
        if (score >= 0.8) return 'quality-high';
        if (score >= 0.5) return 'quality-medium';
        return 'quality-low';
    }

    /**
     * 切换图片选择状态
     */
    toggleSelection(imageId) {
        if (this.selectedImages.has(imageId)) {
            this.selectedImages.delete(imageId);
        } else {
            this.selectedImages.add(imageId);
        }
        this.updateSelectionDisplay();
    }

    /**
     * 更新选择状态显示
     */
    updateSelectionDisplay() {
        const selectedCount = document.getElementById('selectedCount');
        if (selectedCount) {
            selectedCount.textContent = this.selectedImages.size;
        }

        // 更新卡片选择状态
        document.querySelectorAll('.image-card').forEach(card => {
            const imageId = card.dataset.imageId;
            if (this.selectedImages.has(imageId)) {
                card.classList.add('selected');
            } else {
                card.classList.remove('selected');
            }
        });
    }

    /**
     * 全选可见图片
     */
    selectAllVisible() {
        this.filteredImages.forEach(image => {
            this.selectedImages.add(image.id);
        });
        this.updateSelectionDisplay();
    }

    /**
     * 反选可见图片
     */
    invertSelection() {
        const visibleIds = new Set(this.filteredImages.map(img => img.id));
        
        this.filteredImages.forEach(image => {
            if (this.selectedImages.has(image.id)) {
                this.selectedImages.delete(image.id);
            } else {
                this.selectedImages.add(image.id);
            }
        });
        
        this.updateSelectionDisplay();
    }

    /**
     * 清空选择
     */
    clearSelection() {
        this.selectedImages.clear();
        this.updateSelectionDisplay();
    }

    /**
     * 切换多选模式
     */
    toggleSelectionMode() {
        this.selectionMode = !this.selectionMode;
        
        const selectionModeBtn = document.getElementById('selectionModeBtn');
        const galleryContainer = document.querySelector('.gallery-container');
        
        if (this.selectionMode) {
            selectionModeBtn.classList.add('active');
            selectionModeBtn.querySelector('.btn-text').textContent = '退出选择';
            selectionModeBtn.querySelector('i').className = 'fas fa-times';
            galleryContainer.classList.add('selection-mode');
        } else {
            selectionModeBtn.classList.remove('active');
            selectionModeBtn.querySelector('.btn-text').textContent = '选择';
            selectionModeBtn.querySelector('i').className = 'fas fa-mouse-pointer';
            galleryContainer.classList.remove('selection-mode');
            this.clearSelection();
        }
        
        this.updateSelectionDisplay();
    }

    /**
     * 切换收藏状态
     */
    toggleFavorite(imageId) {
        if (this.favorites.has(imageId)) {
            this.favorites.delete(imageId);
        } else {
            this.favorites.add(imageId);
        }
        
        this.saveUserPreferences();
        this.updateFavoritesDisplay();
        
        // 更新卡片显示
        const card = document.querySelector(`[data-image-id="${imageId}"]`);
        if (card) {
            const favoriteBtn = card.querySelector('.action-btn.favorite');
            if (favoriteBtn) {
                favoriteBtn.classList.toggle('active', this.favorites.has(imageId));
            }
        }
    }

    /**
     * 更新收藏显示
     */
    updateFavoritesDisplay() {
        const favoriteCount = document.getElementById('favoriteCount');
        if (favoriteCount) {
            favoriteCount.textContent = this.favorites.size;
        }
    }

    /**
     * 切换仅显示收藏
     */
    toggleFavoritesOnly() {
        this.currentFilters.favoritesOnly = !this.currentFilters.favoritesOnly;
        this.applyFilters();
        
        const showFavoritesBtn = document.getElementById('showFavoritesBtn');
        if (showFavoritesBtn) {
            showFavoritesBtn.textContent = this.currentFilters.favoritesOnly ? 
                '显示全部' : '仅显示收藏';
        }
    }

    /**
     * 切换视图模式
     */
    switchView(viewType) {
        this.currentView = viewType;
        
        // 更新按钮状态
        document.querySelectorAll('.view-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.view === viewType);
        });

        // 更新网格类名
        const galleryGrid = document.getElementById('galleryGrid');
        if (galleryGrid) {
            galleryGrid.className = `gallery-grid ${viewType}-view`;
        }
    }

    /**
     * 更新图片大小
     */
    updateImageSize(size) {
        document.documentElement.style.setProperty('--image-size', `${size}px`);
    }

    /**
     * 打开模态框
     */
    openModal(imageId) {
        const image = this.images.find(img => img.id === imageId);
        if (!image) return;

        this.currentModalImageId = imageId;
        const modal = document.getElementById('imageModal');
        
        // 填充模态框内容
        this.populateModal(image);
        
        // 显示模态框
        modal.classList.add('show');
        document.body.style.overflow = 'hidden';
    }

    /**
     * 填充模态框内容
     */
    populateModal(image) {
        // 基本信息
        document.getElementById('infoTaskId').textContent = image.taskId;
        document.getElementById('infoCreatedAt').textContent = new Date(image.createdAt).toLocaleString();
        document.getElementById('infoGenerationTime').textContent = `${image.generationTime.toFixed(1)}s`;
        document.getElementById('infoQualityScore').textContent = `${(image.qualityScore * 100).toFixed(0)}%`;
        document.getElementById('infoFileSize').textContent = `${image.fileSize.toFixed(1)}MB`;
        document.getElementById('infoResolution').textContent = image.resolution;
        
        // 提示词
        document.getElementById('infoPrompt').textContent = image.prompt;
        
        // 用户标签和系统标签
        this.updateTagsDisplay(image.id);
        
        // 工作流参数
        const paramsContainer = document.getElementById('infoWorkflowParams');
        paramsContainer.innerHTML = `
            <div>步骤数: ${image.workflowParams?.steps || 'N/A'}</div>
            <div>CFG: ${image.workflowParams?.cfg || 'N/A'}</div>
            <div>种子: ${image.workflowParams?.seed || 'N/A'}</div>
        `;
        
        // 图片
        const modalImage = document.getElementById('modalImage');
        modalImage.src = image.src || `/api/image/${image.filename}`;
        modalImage.alt = image.prompt;
        
        // 更新用户评分（优先）或系统质量分
        const userRating = this.userRatings.get(image.id);
        if (userRating) {
            this.updateStarRating(userRating);
        } else {
            this.updateStarRating(Math.round(image.qualityScore * 5));
        }
        
        // 更新收藏按钮
        const favoriteBtn = document.getElementById('toggleFavoriteBtn');
        if (favoriteBtn) {
            const isFavorite = this.favorites.has(image.id);
            favoriteBtn.innerHTML = `<i class="fas fa-heart"></i> ${isFavorite ? '取消收藏' : '收藏'}`;
            favoriteBtn.classList.toggle('active', isFavorite);
        }
    }

    /**
     * 更新星级评分显示
     */
    updateStarRating(rating) {
        const stars = document.querySelectorAll('#starRating i');
        stars.forEach((star, index) => {
            star.classList.toggle('active', index < Math.round(rating));
        });
    }

    /**
     * 评分图片
     */
    rateImage(imageId, rating) {
        const image = this.images.find(img => img.id === imageId);
        if (image) {
            image.qualityScore = rating / 5;
            this.updateStarRating(rating);
            this.showToast('评分已更新', 'success');
        }
    }

    /**
     * 关闭模态框
     */
    closeModal() {
        const modal = document.getElementById('imageModal');
        modal.classList.remove('show');
        document.body.style.overflow = '';
        this.currentModalImageId = null;
    }

    /**
     * 下载图片
     */
    downloadImage(imageId) {
        const image = this.images.find(img => img.id === imageId);
        if (image) {
            const link = document.createElement('a');
            link.href = image.src || `/api/image/${image.filename}`;
            link.download = image.filename;
            link.click();
            this.showToast('开始下载', 'info');
        }
    }

    /**
     * 复制提示词
     */
    copyPrompt(imageId) {
        const image = this.images.find(img => img.id === imageId);
        if (image) {
            navigator.clipboard.writeText(image.prompt).then(() => {
                this.showToast('提示词已复制到剪贴板', 'success');
            }).catch(() => {
                this.showToast('复制失败', 'error');
            });
        }
    }

    /**
     * 为图片评分
     */
    rateImage(imageId, rating) {
        if (!imageId || rating < 1 || rating > 5) return;
        
        this.userRatings.set(imageId, rating);
        this.updateStarRating(rating);
        this.saveUserPreferences();
        this.showToast(`已评分 ${rating} 星`, 'success');
    }

    /**
     * 更新星级评分显示
     */
    updateStarRating(rating) {
        const stars = document.querySelectorAll('#starRating i');
        stars.forEach((star, index) => {
            if (index < rating) {
                star.classList.add('active');
            } else {
                star.classList.remove('active');
            }
        });
    }

    /**
     * 为当前图片添加标签
     */
    addTagToCurrentImage() {
        const tagInput = document.getElementById('tagInput');
        if (!tagInput || !this.currentModalImageId) return;

        const tagText = tagInput.value.trim();
        if (!tagText) return;

        this.addTag(this.currentModalImageId, tagText);
        tagInput.value = '';
    }

    /**
     * 为图片添加标签
     */
    addTag(imageId, tag) {
        if (!imageId || !tag) return;

        let tags = this.userTags.get(imageId) || [];
        
        // 检查是否已存在
        if (tags.includes(tag)) {
            this.showToast('标签已存在', 'warning');
            return;
        }

        tags.push(tag);
        this.userTags.set(imageId, tags);
        
        // 添加到热门标签
        if (!this.popularTags.includes(tag)) {
            this.popularTags.push(tag);
        }

        this.updateTagsDisplay(imageId);
        this.saveUserPreferences();
        this.showToast('标签已添加', 'success');
    }

    /**
     * 移除图片标签
     */
    removeTag(imageId, tag) {
        let tags = this.userTags.get(imageId) || [];
        tags = tags.filter(t => t !== tag);
        
        if (tags.length === 0) {
            this.userTags.delete(imageId);
        } else {
            this.userTags.set(imageId, tags);
        }

        this.updateTagsDisplay(imageId);
        this.saveUserPreferences();
        this.showToast('标签已移除', 'success');
    }

    /**
     * 更新标签显示
     */
    updateTagsDisplay(imageId) {
        const tagsContainer = document.getElementById('infoTags');
        const popularTagsList = document.getElementById('popularTagsList');
        
        if (tagsContainer && imageId === this.currentModalImageId) {
            const tags = this.userTags.get(imageId) || [];
            
            if (tags.length === 0) {
                tagsContainer.innerHTML = '<span class="text-muted">暂无标签</span>';
            } else {
                tagsContainer.innerHTML = tags.map(tag => `
                    <span class="tag removable">
                        ${tag}
                        <button class="tag-remove" onclick="galleryManager.removeTag('${imageId}', '${tag}')">
                            <i class="fas fa-times"></i>
                        </button>
                    </span>
                `).join('');
            }
        }

        // 更新热门标签
        if (popularTagsList) {
            popularTagsList.innerHTML = this.popularTags.slice(0, 8).map(tag => 
                `<span class="popular-tag" onclick="galleryManager.addTag('${this.currentModalImageId}', '${tag}')">${tag}</span>`
            ).join('');
        }
    }

    /**
     * 导出选中的图片
     */
    exportSelected(format = 'json') {
        if (this.selectedImages.size === 0) {
            this.showToast('请先选择要导出的图片', 'warning');
            return;
        }

        const selectedData = Array.from(this.selectedImages).map(id => {
            return this.images.find(img => img.id === id);
        }).filter(Boolean);

        const exportData = {
            exportedAt: new Date().toISOString(),
            count: selectedData.length,
            format: format,
            images: selectedData.map(img => ({
                id: img.id,
                filename: img.filename,
                prompt: img.prompt,
                qualityScore: img.qualityScore,
                createdAt: img.createdAt,
                systemTags: img.tags || [],
                userTags: this.userTags.get(img.id) || [],
                userRating: this.userRatings.get(img.id) || null,
                isFavorite: this.favorites.has(img.id),
                workflowParams: img.workflowParams || {}
            }))
        };

        let content, mimeType, fileExtension;

        switch (format) {
            case 'csv':
                content = this.convertToCSV(exportData.images);
                mimeType = 'text/csv';
                fileExtension = 'csv';
                break;
            case 'json':
            default:
                content = JSON.stringify(exportData, null, 2);
                mimeType = 'application/json';
                fileExtension = 'json';
                break;
        }

        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `gallery_export_${new Date().toISOString().split('T')[0]}.${fileExtension}`;
        link.click();
        URL.revokeObjectURL(url);

        this.showToast(`已导出 ${selectedData.length} 张图片 (${format.toUpperCase()})`, 'success');
    }

    /**
     * 导出文件路径列表
     */
    exportFilePaths() {
        if (this.selectedImages.size === 0) {
            this.showToast('请先选择要导出的图片', 'warning');
            return;
        }

        const selectedData = Array.from(this.selectedImages).map(id => {
            return this.images.find(img => img.id === id);
        }).filter(Boolean);

        const pathList = selectedData.map(img => img.filename).join('\n');

        const blob = new Blob([pathList], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `image_paths_${new Date().toISOString().split('T')[0]}.txt`;
        link.click();
        URL.revokeObjectURL(url);

        this.showToast(`已导出 ${selectedData.length} 个文件路径`, 'success');
    }

    /**
     * 转换为CSV格式
     */
    convertToCSV(images) {
        const headers = [
            'ID', '文件名', '提示词', '质量评分', '创建时间', 
            '系统标签', '用户标签', '用户评分', '是否收藏'
        ];

        const rows = images.map(img => [
            img.id,
            img.filename,
            `"${img.prompt.replace(/"/g, '""')}"`,
            img.qualityScore,
            img.createdAt,
            `"${img.systemTags.join(', ')}"`,
            `"${img.userTags.join(', ')}"`,
            img.userRating || '',
            img.isFavorite ? '是' : '否'
        ]);

        return [headers, ...rows].map(row => row.join(',')).join('\n');
    }

    /**
     * 批量添加标签
     */
    addBatchTag() {
        const input = document.getElementById('batchTagInput');
        if (!input) return;

        const tag = input.value.trim();
        if (!tag) {
            this.showToast('请输入标签名称', 'warning');
            return;
        }

        if (this.selectedImages.size === 0) {
            this.showToast('请先选择要添加标签的图片', 'warning');
            return;
        }

        let addedCount = 0;
        this.selectedImages.forEach(imageId => {
            let tags = this.userTags.get(imageId) || [];
            if (!tags.includes(tag)) {
                tags.push(tag);
                this.userTags.set(imageId, tags);
                addedCount++;
            }
        });

        if (addedCount > 0) {
            // 添加到热门标签
            if (!this.popularTags.includes(tag)) {
                this.popularTags.push(tag);
            }

            this.saveUserPreferences();
            input.value = '';
            this.showToast(`已为 ${addedCount} 张图片添加标签 "${tag}"`, 'success');
        } else {
            this.showToast('所选图片已包含该标签', 'warning');
        }
    }

    /**
     * 切换下拉菜单显示状态
     */
    toggleDropdown(menuId) {
        const menu = document.getElementById(menuId);
        if (!menu) return;

        const isShown = menu.classList.contains('show');
        
        // 关闭所有下拉菜单
        document.querySelectorAll('.dropdown-menu').forEach(m => m.classList.remove('show'));
        
        // 切换当前菜单
        if (!isShown) {
            menu.classList.add('show');
        }
    }

    /**
     * 删除选中的图片
     */
    deleteSelected() {
        if (this.selectedImages.size === 0) {
            this.showToast('请先选择要删除的图片', 'warning');
            return;
        }

        if (confirm(`确定要删除选中的 ${this.selectedImages.size} 张图片吗？`)) {
            // 从数据中移除
            this.images = this.images.filter(img => !this.selectedImages.has(img.id));
            
            // 清空选择
            this.selectedImages.clear();
            
            // 重新应用筛选
            this.applyFilters();
            
            this.showToast('图片已删除', 'success');
        }
    }

    /**
     * 更新统计信息
     */
    updateStats() {
        const totalImages = document.getElementById('totalImages');
        const successRate = document.getElementById('successRate');
        const totalGenerated = document.getElementById('totalGenerated');
        const avgTime = document.getElementById('avgTime');
        const highQualityCount = document.getElementById('highQualityCount');
        const totalSize = document.getElementById('totalSize');

        if (totalImages) totalImages.textContent = this.images.length;
        
        if (successRate) {
            const completedCount = this.images.filter(img => img.status === 'completed').length;
            const rate = this.images.length > 0 ? (completedCount / this.images.length * 100).toFixed(1) : 0;
            successRate.textContent = `${rate}%`;
        }

        if (totalGenerated) totalGenerated.textContent = this.images.length;
        
        if (avgTime) {
            const avg = this.images.length > 0 ? 
                (this.images.reduce((sum, img) => sum + img.generationTime, 0) / this.images.length).toFixed(1) : 0;
            avgTime.textContent = avg;
        }

        if (highQualityCount) {
            const highQuality = this.images.filter(img => img.qualityScore >= 0.8).length;
            highQualityCount.textContent = highQuality;
        }

        if (totalSize) {
            const total = this.images.reduce((sum, img) => sum + img.fileSize, 0);
            totalSize.textContent = total.toFixed(1);
        }
    }

    /**
     * 更新标签显示
     */
    updateTags() {
        const tagsContainer = document.getElementById('tagsContainer');
        if (!tagsContainer) return;

        // 收集所有标签
        const allTags = new Set();
        this.images.forEach(img => {
            img.tags.forEach(tag => allTags.add(tag));
        });

        // 渲染标签
        tagsContainer.innerHTML = Array.from(allTags).map(tag => `
            <div class="tag-item" data-tag="${tag}">${tag}</div>
        `).join('');

        // 绑定标签点击事件
        tagsContainer.addEventListener('click', (e) => {
            if (e.target.classList.contains('tag-item')) {
                const tag = e.target.dataset.tag;
                this.toggleTagFilter(tag);
            }
        });
    }

    /**
     * 切换标签筛选
     */
    toggleTagFilter(tag) {
        const tagElement = document.querySelector(`[data-tag="${tag}"]`);
        
        if (this.currentFilters.tags.includes(tag)) {
            this.currentFilters.tags = this.currentFilters.tags.filter(t => t !== tag);
            tagElement.classList.remove('active');
        } else {
            this.currentFilters.tags.push(tag);
            tagElement.classList.add('active');
        }
        
        this.applyFilters();
    }

    /**
     * 显示/隐藏加载指示器
     */
    showLoading(show) {
        const loadingOverlay = document.getElementById('loadingOverlay');
        if (loadingOverlay) {
            loadingOverlay.classList.toggle('show', show);
        }
    }

    /**
     * 显示/隐藏无结果提示
     */
    showNoResults(show) {
        const noResults = document.getElementById('noResults');
        if (noResults) {
            noResults.style.display = show ? 'block' : 'none';
        }
    }

    /**
     * 显示提示消息
     */
    showToast(message, type = 'info') {
        const toast = document.getElementById('toast');
        if (!toast) return;

        const icon = toast.querySelector('.toast-icon');
        const messageEl = toast.querySelector('.toast-message');

        // 设置图标
        icon.className = 'toast-icon';
        switch (type) {
            case 'success':
                icon.classList.add('fas', 'fa-check-circle');
                break;
            case 'error':
                icon.classList.add('fas', 'fa-exclamation-circle');
                break;
            case 'warning':
                icon.classList.add('fas', 'fa-exclamation-triangle');
                break;
            default:
                icon.classList.add('fas', 'fa-info-circle');
        }

        messageEl.textContent = message;
        toast.className = `toast ${type}`;
        toast.classList.add('show');

        // 自动隐藏
        setTimeout(() => {
            toast.classList.remove('show');
        }, 3000);
    }

    /**
     * 加载用户偏好设置
     */
    loadUserPreferences() {
        try {
            const saved = localStorage.getItem('galleryPreferences');
            if (saved) {
                const prefs = JSON.parse(saved);
                
                // 基础偏好
                this.favorites = new Set(prefs.favorites || []);
                this.currentView = prefs.view || 'grid';
                this.currentSort = prefs.sort || 'date_desc';
                
                // 用户标签和评分
                if (prefs.userTags) {
                    this.userTags = new Map(Object.entries(prefs.userTags));
                }
                if (prefs.userRatings) {
                    this.userRatings = new Map(Object.entries(prefs.userRatings));
                }
                if (prefs.popularTags) {
                    this.popularTags = [...this.popularTags, ...prefs.popularTags]
                        .filter((tag, index, arr) => arr.indexOf(tag) === index)
                        .slice(0, 20); // 限制热门标签数量
                }
                
                // 筛选偏好
                if (prefs.filters) {
                    this.currentFilters = { ...this.currentFilters, ...prefs.filters };
                }
                
                // 界面偏好
                if (prefs.ui) {
                    this.selectionMode = prefs.ui.selectionMode || false;
                }
            }
        } catch (error) {
            console.error('加载用户偏好失败:', error);
        }
    }

    /**
     * 保存用户偏好设置
     */
    saveUserPreferences() {
        try {
            const prefs = {
                // 基础偏好
                favorites: Array.from(this.favorites),
                view: this.currentView,
                sort: this.currentSort,
                
                // 用户数据
                userTags: Object.fromEntries(this.userTags),
                userRatings: Object.fromEntries(this.userRatings),
                popularTags: this.popularTags,
                
                // 筛选偏好（排除临时搜索）
                filters: {
                    dateFrom: this.currentFilters.dateFrom,
                    dateTo: this.currentFilters.dateTo,
                    status: this.currentFilters.status,
                    qualityMin: this.currentFilters.qualityMin,
                    tags: this.currentFilters.tags,
                    favoritesOnly: this.currentFilters.favoritesOnly
                },
                
                // 界面偏好
                ui: {
                    selectionMode: this.selectionMode
                },
                
                // 元数据
                lastSaved: new Date().toISOString(),
                version: '1.0'
            };
            
            localStorage.setItem('galleryPreferences', JSON.stringify(prefs));
        } catch (error) {
            console.error('保存用户偏好失败:', error);
        }
    }

    /**
     * 重置用户偏好
     */
    resetPreferences() {
        if (confirm('确定要重置所有用户偏好设置吗？这将清除收藏、标签、评分等所有数据。')) {
            localStorage.removeItem('galleryPreferences');
            
            // 重置内存中的数据
            this.favorites.clear();
            this.userTags.clear();
            this.userRatings.clear();
            this.currentView = 'grid';
            this.currentSort = 'date_desc';
            this.selectionMode = false;
            this.popularTags = ['高质量', '人像', '风景', '动漫', '写实', '艺术'];
            this.currentFilters = {
                search: '',
                dateFrom: '',
                dateTo: '',
                status: ['completed'],
                qualityMin: 0,
                tags: [],
                favoritesOnly: false
            };
            
            this.showToast('用户偏好已重置', 'success');
            this.updateDisplay();
        }
    }

    /**
     * 导出用户偏好
     */
    exportPreferences() {
        try {
            const saved = localStorage.getItem('galleryPreferences');
            if (!saved) {
                this.showToast('没有可导出的用户偏好', 'warning');
                return;
            }

            const blob = new Blob([saved], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `gallery_preferences_${new Date().toISOString().split('T')[0]}.json`;
            link.click();
            URL.revokeObjectURL(url);

            this.showToast('用户偏好导出成功', 'success');
        } catch (error) {
            console.error('导出偏好失败:', error);
            this.showToast('导出失败', 'error');
        }
    }

    /**
     * 导入用户偏好
     */
    importPreferences(file) {
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const importedPrefs = JSON.parse(e.target.result);
                
                // 验证数据格式
                if (!importedPrefs.version) {
                    throw new Error('不支持的偏好文件格式');
                }

                localStorage.setItem('galleryPreferences', JSON.stringify(importedPrefs));
                this.loadUserPreferences();
                this.updateDisplay();
                
                this.showToast('用户偏好导入成功', 'success');
            } catch (error) {
                console.error('导入偏好失败:', error);
                this.showToast('导入失败：文件格式错误', 'error');
            }
        };
        
        reader.readAsText(file);
    }
}

// 全局实例
let galleryManager;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    galleryManager = new GalleryManager();
});

// 键盘快捷键
document.addEventListener('keydown', (e) => {
    if (!galleryManager) return;

    // ESC 关闭模态框
    if (e.key === 'Escape') {
        galleryManager.closeModal();
    }
    
    // Ctrl+A 全选
    if (e.ctrlKey && e.key === 'a') {
        e.preventDefault();
        galleryManager.selectAllVisible();
    }
    
    // Delete 删除选中
    if (e.key === 'Delete' && galleryManager.selectedImages.size > 0) {
        galleryManager.deleteSelected();
    }
});

