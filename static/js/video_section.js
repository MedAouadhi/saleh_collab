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
                    if (gen.status === 'pending' || gen.status === 'in_progress' || gen.status === 'processing' || gen.status === 'queued') {
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
                console.log('[submitGeneration] response:', data);
                if (data.success && data.generation) {
                    const gen = {
                        ...data.generation,
                        prompt: scene.newPrompt,
                        model: scene.newModel,
                        resolution: scene.newResolution,
                        aspect_ratio: scene.newAspectRatio,
                        generate_audio: scene.newAudio,
                        drive_file_id: null,
                        drive_view_url: null,
                        local_path: null,
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
                console.error('[submitGeneration] error:', e);
                alert('خطأ في الشبكة');
            } finally {
                scene.submitting = false;
            }
        },

        startPolling(gen) {
            if (this.pollIntervals[gen.id]) return;
            console.log('[startPolling] starting polling for gen', gen.id, 'current status:', gen.status);
            this.pollIntervals[gen.id] = setInterval(async () => {
                try {
                    const resp = await fetch(`/api/generations/${gen.id}/status`);
                    const data = await resp.json();
                    console.log('[poll] gen', gen.id, 'response:', data);
                    if (data.success && data.generation) {
                        this._updateGeneration(gen, data.generation);
                        if (['completed', 'failed', 'cancelled', 'expired'].includes(gen.status)) {
                            console.log('[poll] gen', gen.id, 'reached terminal status:', gen.status, 'stopping polling');
                            clearInterval(this.pollIntervals[gen.id]);
                            delete this.pollIntervals[gen.id];
                        }
                    }
                } catch (e) {
                    console.error('Polling error:', e);
                }
            }, 10000); // 10 seconds
        },

        // Replace the generation object in its array so Alpine.js detects the change
        _updateGeneration(gen, updates) {
            for (const scene of this.scenes) {
                const idx = scene.generations.findIndex(g => g.id === gen.id);
                if (idx !== -1) {
                    scene.generations[idx] = { ...scene.generations[idx], ...updates };
                    console.log('[updateGeneration] replaced gen at scene', scene.number, 'index', idx, 'new status:', updates.status);
                    return;
                }
            }
        },

        async downloadVideo(genId) {
            console.log('[downloadVideo] called with genId:', genId, 'type:', typeof genId);
            const gen = this.findGeneration(genId);
            console.log('[downloadVideo] found gen:', gen);
            if (!gen) {
                console.error('[downloadVideo] generation not found for id:', genId);
                alert('لم يتم العثور على العملية');
                return;
            }
            gen.downloading = true;
            try {
                console.log('[downloadVideo] sending POST to /api/generations/' + genId + '/download');
                const resp = await fetch(`/api/generations/${genId}/download`, { method: 'POST' });
                console.log('[downloadVideo] response status:', resp.status);
                const data = await resp.json();
                console.log('[downloadVideo] response data:', data);
                if (data.success) {
                    this._updateGeneration(gen, { local_path: data.local_path });
                } else {
                    alert(data.message || 'فشل التحميل');
                }
            } catch (e) {
                console.error('[downloadVideo] error:', e);
                alert('خطأ في الشبكة');
            } finally {
                gen.downloading = false;
            }
        },

        async saveToDrive(genId) {
            console.log('[saveToDrive] called with genId:', genId);
            const gen = this.findGeneration(genId);
            console.log('[saveToDrive] found gen:', gen);
            if (!gen) {
                alert('لم يتم العثور على العملية');
                return;
            }
            gen.saving = true;
            try {
                const resp = await fetch(`/api/generations/${genId}/save-to-drive`, { method: 'POST' });
                const data = await resp.json();
                console.log('[saveToDrive] response:', data);
                if (data.success) {
                    this._updateGeneration(gen, {
                        drive_file_id: data.drive_file_id,
                        drive_view_url: data.drive_view_url,
                        local_path: null,
                    });
                } else {
                    alert(data.message || 'فشل الرفع إلى Drive');
                }
            } catch (e) {
                console.error('[saveToDrive] error:', e);
                alert('خطأ في الشبكة');
            } finally {
                gen.saving = false;
            }
        },

        async checkStatus(gen) {
            // Manual status check button
            console.log('[checkStatus] manual check for gen', gen.id);
            try {
                const resp = await fetch(`/api/generations/${gen.id}/status`);
                const data = await resp.json();
                console.log('[checkStatus] response:', data);
                if (data.success && data.generation) {
                    this._updateGeneration(gen, data.generation);
                }
            } catch (e) {
                console.error('[checkStatus] error:', e);
                alert('خطأ في الاتصال');
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
            console.log('[findGeneration] searching for genId:', genId, 'type:', typeof genId);
            for (const scene of this.scenes) {
                const gen = scene.generations.find(g => {
                    const match = g.id == genId;
                    console.log('[findGeneration] comparing g.id:', g.id, 'type:', typeof g.id, 'with genId:', genId, 'type:', typeof genId, 'match:', match);
                    return match;
                });
                if (gen) return gen;
            }
            return null;
        },
    };
}