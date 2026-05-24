// static/js/video_section.js
// Alpine.js data component for the video generation section.

function videoSection() {
    return {
        open: false,
        scenes: INITIAL_SCENES || [],
        availableModels: [],
        modelsLoading: false,
        modelsError: null,
        isAssigned: IS_ASSIGNED || false,
        isAdmin: IS_ADMIN || false,
        episodeId: EPISODE_ID || null,
        addingScene: false,
        pollIntervals: {},

        initVideoSection() {
            // Open first scene by default
            this.scenes.forEach((s, i) => { s.open = i === 0; });
            this.fetchModels();
            // Resume polling for any in-progress generations
            this.scenes.forEach(scene => {
                scene.generations.forEach(gen => {
                    if (gen.status === 'pending' || gen.status === 'in_progress') {
                        this.startPolling(gen);
                    }
                });
            });
        },

        async fetchModels() {
            this.modelsLoading = true;
            this.modelsError = null;
            try {
                const resp = await fetch('/api/models');
                const data = await resp.json();
                if (data.success) {
                    this.availableModels = data.models;
                } else {
                    this.modelsError = data.message || 'فشل تحميل الموديلات';
                }
            } catch (e) {
                this.modelsError = 'خطأ في الاتصال بـ OpenRouter';
            } finally {
                this.modelsLoading = false;
            }
        },

        updateModelOptions(scene) {
            const model = this.availableModels.find(m => m.id === scene.newModel);
            if (model) {
                scene.availableResolutions = model.supported_resolutions || [];
                scene.availableAspectRatios = model.supported_aspect_ratios || [];
            } else {
                scene.availableResolutions = [];
                scene.availableAspectRatios = [];
            }
            scene.newResolution = '';
            scene.newAspectRatio = '';
        },

        async addScene() {
            this.addingScene = true;
            try {
                const resp = await fetch(`/api/episodes/${this.episodeId}/scenes`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                });
                const data = await resp.json();
                if (data.success) {
                    this.scenes.push({
                        id: data.scene.id,
                        number: data.scene.number,
                        open: true,
                        generations: [],
                        newPrompt: '',
                        newModel: '',
                        newResolution: '',
                        newAspectRatio: '',
                        newAudio: true,
                        availableResolutions: [],
                        availableAspectRatios: [],
                        submitting: false,
                    });
                } else {
                    alert(data.message || 'فشل إنشاء المشهد');
                }
            } catch (e) {
                alert('خطأ في الشبكة');
            } finally {
                this.addingScene = false;
            }
        },

        async deleteScene(sceneId) {
            if (!confirm('هل أنت متأكد من حذف هذا المشهد وجميع عمليات التوليد؟')) return;
            try {
                const resp = await fetch(`/api/scenes/${sceneId}`, { method: 'DELETE' });
                const data = await resp.json();
                if (data.success) {
                    this.scenes = this.scenes.filter(s => s.id !== sceneId);
                } else {
                    alert(data.message || 'فشل الحذف');
                }
            } catch (e) {
                alert('خطأ في الشبكة');
            }
        },

        async submitGeneration(scene) {
            scene.submitting = true;
            try {
                const resp = await fetch(`/api/scenes/${scene.id}/generations`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        prompt: scene.newPrompt,
                        model: scene.newModel,
                        resolution: scene.newResolution,
                        aspect_ratio: scene.newAspectRatio,
                        generate_audio: scene.newAudio,
                    }),
                });
                const data = await resp.json();
                if (data.success && data.generation) {
                    const gen = {
                        ...data.generation,
                        prompt: scene.newPrompt,
                        model: scene.newModel,
                        resolution: scene.newResolution,
                        aspect_ratio: scene.newAspectRatio,
                        generate_audio: scene.newAudio,
                        showPlayer: false,
                        downloading: false,
                        saving: false,
                    };
                    scene.generations.unshift(gen);
                    scene.newPrompt = '';
                    scene.newModel = '';
                    scene.newResolution = '';
                    scene.newAspectRatio = '';
                    scene.newAudio = true;
                    this.startPolling(gen);
                } else {
                    alert(data.message || 'فشل إنشاء عملية التوليد');
                }
            } catch (e) {
                alert('خطأ في الشبكة');
            } finally {
                scene.submitting = false;
            }
        },

        startPolling(gen) {
            if (this.pollIntervals[gen.id]) return;
            this.pollIntervals[gen.id] = setInterval(async () => {
                try {
                    const resp = await fetch(`/api/generations/${gen.id}/status`);
                    const data = await resp.json();
                    if (data.success && data.generation) {
                        Object.assign(gen, data.generation);
                        if (['completed', 'failed', 'cancelled', 'expired'].includes(gen.status)) {
                            clearInterval(this.pollIntervals[gen.id]);
                            delete this.pollIntervals[gen.id];
                        }
                    }
                } catch (e) {
                    console.error('Polling error:', e);
                }
            }, 10000); // 10 seconds
        },

        async downloadVideo(genId) {
            const gen = this.findGeneration(genId);
            if (!gen) return;
            gen.downloading = true;
            try {
                const resp = await fetch(`/api/generations/${genId}/download`, { method: 'POST' });
                const data = await resp.json();
                if (data.success) {
                    gen.local_path = data.local_path;
                } else {
                    alert(data.message || 'فشل التحميل');
                }
            } catch (e) {
                alert('خطأ في الشبكة');
            } finally {
                gen.downloading = false;
            }
        },

        async saveToDrive(genId) {
            const gen = this.findGeneration(genId);
            if (!gen) return;
            gen.saving = true;
            try {
                const resp = await fetch(`/api/generations/${genId}/save-to-drive`, { method: 'POST' });
                const data = await resp.json();
                if (data.success) {
                    gen.drive_file_id = data.drive_file_id;
                    gen.drive_view_url = data.drive_view_url;
                    gen.local_path = null;
                } else {
                    alert(data.message || 'فشل الرفع إلى Drive');
                }
            } catch (e) {
                alert('خطأ في الشبكة');
            } finally {
                gen.saving = false;
            }
        },

        playVideo(gen) {
            gen.showPlayer = !gen.showPlayer;
        },

        async deleteGeneration(genId) {
            if (!confirm('هل أنت متأكد من حذف هذه العملية؟')) return;
            try {
                const resp = await fetch(`/api/generations/${genId}`, { method: 'DELETE' });
                const data = await resp.json();
                if (data.success) {
                    this.scenes.forEach(scene => {
                        scene.generations = scene.generations.filter(g => g.id !== genId);
                    });
                    if (this.pollIntervals[genId]) {
                        clearInterval(this.pollIntervals[genId]);
                        delete this.pollIntervals[genId];
                    }
                } else {
                    alert(data.message || 'فشل الحذف');
                }
            } catch (e) {
                alert('خطأ في الشبكة');
            }
        },

        findGeneration(genId) {
            for (const scene of this.scenes) {
                const gen = scene.generations.find(g => g.id === genId);
                if (gen) return gen;
            }
            return null;
        },
    };
}
