// static/js/script.js (Arabic Version - Removed jsPDF Logic)

document.addEventListener('DOMContentLoaded', () => {
  console.log('DOM fully loaded and parsed - Main script.js running.');

  // --- Elements ---
  const planArea = document.getElementById('plan-area');
  const savePlanBtn = document.getElementById('save-plan-btn');
  const planStatus = document.getElementById('plan-status');
  const planDisplay = document.getElementById('plan-display');
  const viewPlanBtn = document.getElementById('view-plan-btn');
  const editPlanBtn = document.getElementById('edit-plan-btn');
  const planEditorWrapper = document.getElementById('plan-editor-wrapper');

  const scenarioArea = document.getElementById('scenario-area');
  const saveScenarioBtn = document.getElementById('save-scenario-btn');
  const scenarioStatus = document.getElementById('scenario-status');
  const scenarioDisplay = document.getElementById('scenario-display');
  const viewScenarioBtnActual =
      document.getElementById('view-scenario-btn');  // Corrected ID
  const editScenarioBtnActual =
      document.getElementById('edit-scenario-btn');  // Corrected ID
  const scenarioEditorWrapper =
      document.getElementById('scenario-editor-wrapper');
  const commentInstruction = document.getElementById('comment-instruction');

  const commentDisplayArea = document.getElementById('comment-display-area');
  const commentFormContainer =
      document.getElementById('comment-form-container');
  const commentBlockIndexSpan = document.getElementById('comment-block-index');
  const commentText = document.getElementById('comment-text');
  const submitCommentBtn = document.getElementById('submit-comment-btn');
  const cancelCommentBtn = document.getElementById('cancel-comment-btn');
  const commentStatus = document.getElementById('comment-status');
  const noCommentsMsg = document.getElementById('no-comments-msg');

  // Removed PDF Export button reference
  // const exportPdfBtn = document.getElementById('export-pdf-btn');

  let currentEditingBlock = null;

  // Check if we are on the episode page
  if (typeof EPISODE_ID !== 'undefined' && EPISODE_ID !== null &&
      typeof CURRENT_USER_ID !== 'undefined') {
    console.log('Episode page detected. Initializing episode features.');

    // --- Initial Setup ---
    if (planDisplay && typeof INITIAL_PLAN !== 'undefined')
      renderPlanMarkdown(INITIAL_PLAN);
    if (scenarioDisplay && typeof INITIAL_SCENARIO !== 'undefined')
      renderScenario(INITIAL_SCENARIO);
    if (typeof INITIAL_COMMENTS_BY_BLOCK !== 'undefined')
      renderComments(INITIAL_COMMENTS_BY_BLOCK);

    // Initial view modes
    if (planEditorWrapper) planEditorWrapper.classList.add('hidden');
    if (planDisplay) planDisplay.classList.remove('hidden');
    if (scenarioEditorWrapper) scenarioEditorWrapper.classList.add('hidden');
    if (scenarioDisplay) scenarioDisplay.classList.remove('hidden');
    if (commentInstruction) commentInstruction.style.display = 'block';


    // --- Event Listeners ---

    // Save Plan Button
    if (savePlanBtn && IS_ASSIGNED) {
      savePlanBtn.addEventListener('click', () => {
        saveContent('plan', planArea.value, planStatus).then(success => {
          if (success) renderPlanMarkdown(planArea.value);
        });
      });
    }

    // Save Scenario Button
    if (saveScenarioBtn && IS_ASSIGNED) {
      saveScenarioBtn.addEventListener('click', () => {
        const newScenario = scenarioArea.value;
        saveContent('scenario', newScenario, scenarioStatus).then(success => {
          if (success) renderScenario(scenarioArea.value);
        });
      });
    }

    // --- Plan View/Edit Mode Toggle ---
    if (viewPlanBtn && editPlanBtn && planDisplay && planEditorWrapper &&
        IS_ASSIGNED) {
      viewPlanBtn.addEventListener('click', () => {
        planEditorWrapper.classList.add('hidden');
        planDisplay.classList.remove('hidden');
        renderPlanMarkdown(planArea.value);
        // Update button styles
        viewPlanBtn.classList.add(
            'active', 'bg-indigo-100', 'text-indigo-700', 'font-medium');
        viewPlanBtn.classList.remove('text-gray-600', 'hover:bg-gray-100');
        editPlanBtn.classList.remove(
            'active', 'bg-indigo-100', 'text-indigo-700', 'font-medium');
        editPlanBtn.classList.add('text-gray-600', 'hover:bg-gray-100');
      });
      editPlanBtn.addEventListener('click', () => {
        planDisplay.classList.add('hidden');
        planEditorWrapper.classList.remove('hidden');
        // Update button styles
        editPlanBtn.classList.add(
            'active', 'bg-indigo-100', 'text-indigo-700', 'font-medium');
        editPlanBtn.classList.remove('text-gray-600', 'hover:bg-gray-100');
        viewPlanBtn.classList.remove(
            'active', 'bg-indigo-100', 'text-indigo-700', 'font-medium');
        viewPlanBtn.classList.add('text-gray-600', 'hover:bg-gray-100');
        planArea.focus();
      });
    }

    // --- Scenario View/Edit Mode Toggle ---
    if (viewScenarioBtnActual && editScenarioBtnActual && scenarioDisplay &&
        scenarioEditorWrapper && IS_ASSIGNED) {
      viewScenarioBtnActual.addEventListener('click', () => {
        scenarioEditorWrapper.classList.add('hidden');
        scenarioDisplay.classList.remove('hidden');
        if (commentInstruction) commentInstruction.style.display = 'block';
        renderScenario(scenarioArea.value);
        // Update button styles
        viewScenarioBtnActual.classList.add(
            'active', 'bg-indigo-100', 'text-indigo-700', 'font-medium');
        viewScenarioBtnActual.classList.remove(
            'text-gray-600', 'hover:bg-gray-100');
        editScenarioBtnActual.classList.remove(
            'active', 'bg-indigo-100', 'text-indigo-700', 'font-medium');
        editScenarioBtnActual.classList.add(
            'text-gray-600', 'hover:bg-gray-100');
      });
      editScenarioBtnActual.addEventListener('click', () => {
        scenarioDisplay.classList.add('hidden');
        scenarioEditorWrapper.classList.remove('hidden');
        if (commentInstruction) commentInstruction.style.display = 'none';
        // Update button styles
        editScenarioBtnActual.classList.add(
            'active', 'bg-indigo-100', 'text-indigo-700', 'font-medium');
        editScenarioBtnActual.classList.remove(
            'text-gray-600', 'hover:bg-gray-100');
        viewScenarioBtnActual.classList.remove(
            'active', 'bg-indigo-100', 'text-indigo-700', 'font-medium');
        viewScenarioBtnActual.classList.add(
            'text-gray-600', 'hover:bg-gray-100');
        scenarioArea.focus();
      });
    }

    // --- REMOVED PDF Export Button Listener ---
    // if (exportPdfBtn) { ... }

    // --- Commenting Logic (Scenario Display Click, Submit, Cancel, Delete) ---
    // ... (Existing commenting logic remains here, unchanged) ...
    if (IS_ASSIGNED && scenarioDisplay) {
      scenarioDisplay.addEventListener('click', (event) => {
        if (scenarioDisplay.classList.contains('hidden')) return;
        const targetBlock = event.target.closest('.commentable-block');
        if (targetBlock) {
          const blockIndex = parseInt(targetBlock.dataset.blockIndex, 10);
          if (!isNaN(blockIndex)) {
            openCommentForm(blockIndex);
          }
        }
      });
    }
    if (submitCommentBtn && IS_ASSIGNED) {
      submitCommentBtn.addEventListener('click', () => {
        const blockIndex = currentEditingBlock;
        const text = commentText.value.trim();
        if (!text) {
          commentStatus.textContent = 'نص التعليق لا يمكن أن يكون فارغًا.';
          return;
        }
        if (blockIndex === null || blockIndex < 0) {
          commentStatus.textContent = 'خطأ: لم يتم تحديد فقرة.';
          return;
        }
        submitCommentBtn.disabled = true;
        submitCommentBtn.textContent = 'جارٍ الإرسال...';
        fetch(`/episode/${EPISODE_ID}/comments`, {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({block_index: blockIndex, text: text})
        })
            .then(response => response.json())
            .then(data => {
              if (data.success && data.comment) {
                addCommentToDisplay(data.comment);
                const blockElement = scenarioDisplay.querySelector(
                    `.commentable-block[data-block-index="${blockIndex}"]`);
                if (blockElement) blockElement.classList.add('has-comments');
                closeCommentForm();
              } else {
                commentStatus.textContent =
                    `خطأ: ${data.message || 'فشل إضافة التعليق'}`;
              }
            })
            .catch(error => {
              commentStatus.textContent =
                  'خطأ في الشبكة. يرجى المحاولة مرة أخرى.';
            })
            .finally(() => {
              submitCommentBtn.disabled = false;
              submitCommentBtn.textContent = 'إرسال التعليق';
            });
      });
    }
    if (cancelCommentBtn) {
      cancelCommentBtn.addEventListener('click', () => {
        closeCommentForm();
      });
    }
    if (commentDisplayArea) {
      commentDisplayArea.addEventListener('click', function(event) {
        const deleteButton = event.target.closest('.delete-comment-btn');
        if (deleteButton) {
          const commentElement = deleteButton.closest('.comment-item');
          const commentId = deleteButton.dataset.commentId;
          const lineGroup =
              commentElement ? commentElement.closest('.comment-group') : null;
          const blockIndex = lineGroup ? lineGroup.dataset.blockIndex : null;
          if (commentId && commentElement) {
            const confirmed = confirm('هل أنت متأكد أنك تريد حذف هذا التعليق؟');
            if (confirmed) {
              fetch(
                  `/delete_comment/${commentId}`,
                  {method: 'POST', headers: {'Accept': 'application/json'}})
                  .then(response => response.json())
                  .then(data => {
                    if (data.success) {
                      commentElement.style.transition = 'opacity 0.3s ease-out';
                      commentElement.style.opacity = '0';
                      setTimeout(() => {
                        commentElement.remove();
                        if (lineGroup &&
                            !lineGroup.querySelector('.comment-item')) {
                          lineGroup.remove();
                          if (blockIndex !== null) {
                            const blockElement = scenarioDisplay.querySelector(
                                `.commentable-block[data-block-index="${
                                    blockIndex}"]`);
                            const otherCommentsExist =
                                INITIAL_COMMENTS_BY_BLOCK[blockIndex] &&
                                INITIAL_COMMENTS_BY_BLOCK[blockIndex].some(
                                    c => c.id !== parseInt(commentId));
                            const otherDynamicCommentsExist =
                                lineGroup.querySelector('.comment-item');
                            if (blockElement && !otherCommentsExist &&
                                !otherDynamicCommentsExist) {
                              blockElement.classList.remove('has-comments');
                            }
                          }
                        }
                        if (!commentDisplayArea.querySelector(
                                '.comment-group')) {
                          if (noCommentsMsg)
                            noCommentsMsg.style.display = 'block';
                        }
                      }, 300);
                    } else {
                      alert(`خطأ في حذف التعليق: ${data.message}`);
                    }
                  })
                  .catch(error => {
                    alert('خطأ في الشبكة أثناء محاولة حذف التعليق.');
                  });
            }
          }
        }
      });
    }


    // --- Helper Functions ---

    async function saveContent(type, content, statusElement) {
      // ... (saveContent logic updated to re-render markdown) ...
      statusElement.textContent = 'جارٍ الحفظ...';
      statusElement.classList.remove('text-green-600', 'text-red-600');
      statusElement.classList.add('text-gray-500');
      try {
        const response = await fetch(`/episode/${EPISODE_ID}/update`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({[type]: content})
        });
        const data = await response.json();
        if (response.ok && data.success) {
          statusElement.textContent = 'تم الحفظ بنجاح!';
          statusElement.classList.remove('text-gray-500', 'text-red-600');
          statusElement.classList.add('text-green-600');
          setTimeout(() => statusElement.textContent = '', 3000);
          if (type === 'plan') {
            renderPlanMarkdown(content);
          } else if (type === 'scenario') {
            renderScenario(content);
          }
          return true;
        } else {
          throw new Error(data.message || 'فشل الحفظ');
        }
      } catch (error) {
        console.error(`Error saving ${type}:`, error);
        statusElement.textContent = `خطأ: ${error.message}`;
        statusElement.classList.remove('text-gray-500', 'text-green-600');
        statusElement.classList.add('text-red-600');
        return false;
      }
    }

    function renderPlanMarkdown(planText) {
      // ... (renderPlanMarkdown remains the same) ...
      if (!planDisplay || typeof marked === 'undefined') {
        console.error('Plan display area not found or Marked.js not loaded.');
        return;
      }
      try {
        const planHtml = marked.parse(planText || '');
        planDisplay.innerHTML = planHtml;
        console.log('Rendered plan as Markdown.');
      } catch (e) {
        console.error('Error parsing plan Markdown:', e);
        planDisplay.textContent = planText;
      }
    }

    function renderScenario(scenarioText) {
      // ... (renderScenario remains the same) ...
      if (!scenarioDisplay || typeof marked === 'undefined') {
        console.error(
            'Scenario display area not found or Marked.js not loaded.');
        return;
      }
      try {
        const scenarioHtml = marked.parse(scenarioText || '');
        scenarioDisplay.innerHTML = scenarioHtml;
        const children = scenarioDisplay.children;
        let hasCommentableBlocks = false;
        for (let i = 0; i < children.length; i++) {
          const blockElement = children[i];
          blockElement.dataset.blockIndex = i;
          blockElement.classList.add('commentable-block');
          hasCommentableBlocks = true;
          if (typeof INITIAL_COMMENTS_BY_BLOCK !== 'undefined' &&
              INITIAL_COMMENTS_BY_BLOCK[i]) {
            blockElement.classList.add('has-comments');
          }
        }
        if (!hasCommentableBlocks && scenarioText && scenarioText.trim()) {
          scenarioDisplay.innerHTML =
              `<div class="commentable-block" data-block-index="0">${
                  scenarioDisplay.innerHTML}</div>`;
          if (typeof INITIAL_COMMENTS_BY_BLOCK !== 'undefined' &&
              INITIAL_COMMENTS_BY_BLOCK[0]) {
            scenarioDisplay.firstChild.classList.add('has-comments');
          }
        }
        console.log(`Rendered scenario as Markdown, added indices to ${
            children.length} blocks.`);
      } catch (e) {
        console.error('Error during scenario Markdown rendering:', e);
        scenarioDisplay.textContent = scenarioText;
      }
    }

    function renderComments(commentsByBlock) {
      // ... (renderComments remains the same) ...
      if (!commentDisplayArea) return;
      clearCommentsDisplay();
      let hasAnyComments = false;
      if (commentsByBlock && typeof commentsByBlock === 'object') {
        Object.keys(commentsByBlock)
            .sort((a, b) => parseInt(a, 10) - parseInt(b, 10))
            .forEach(blockIndex => {
              const comments = commentsByBlock[blockIndex];
              if (comments && comments.length > 0) {
                hasAnyComments = true;
                const blockCommentsContainer = document.createElement('div');
                blockCommentsContainer.classList.add(
                    'comment-group', 'mb-3', 'border-r-4', 'border-blue-200',
                    'pr-3', 'text-right');
                blockCommentsContainer.dataset.blockIndex = blockIndex;
                const blockHeader = document.createElement('h4');
                blockHeader.classList.add(
                    'text-sm', 'font-semibold', 'text-gray-600', 'mb-1');
                blockHeader.textContent =
                    `تعليقات للفقرة رقم ${parseInt(blockIndex, 10) + 1}`;
                blockCommentsContainer.appendChild(blockHeader);
                comments.forEach(comment => {
                  const commentElement = createCommentElement(comment);
                  blockCommentsContainer.appendChild(commentElement);
                });
                commentDisplayArea.appendChild(blockCommentsContainer);
              }
            });
      }
      if (noCommentsMsg) {
        noCommentsMsg.style.display = hasAnyComments ? 'none' : 'block';
      }
      console.log(
          `Rendered comments by block. Has comments: ${hasAnyComments}`);
    }

    function addCommentToDisplay(comment) {
      // ... (addCommentToDisplay remains the same) ...
      if (!commentDisplayArea || comment.block_index === undefined) return;
      if (noCommentsMsg && noCommentsMsg.style.display !== 'none') {
        noCommentsMsg.style.display = 'none';
      }
      const blockIndex = comment.block_index;
      let blockCommentsContainer = commentDisplayArea.querySelector(
          `.comment-group[data-block-index="${blockIndex}"]`);
      if (!blockCommentsContainer) {
        blockCommentsContainer = document.createElement('div');
        blockCommentsContainer.classList.add(
            'comment-group', 'mb-3', 'border-r-4', 'border-blue-200', 'pr-3',
            'text-right');
        blockCommentsContainer.dataset.blockIndex = blockIndex;
        const blockHeader = document.createElement('h4');
        blockHeader.classList.add(
            'text-sm', 'font-semibold', 'text-gray-600', 'mb-1');
        blockHeader.textContent = `تعليقات للفقرة رقم ${blockIndex + 1}`;
        blockCommentsContainer.appendChild(blockHeader);
        const existingGroups =
            commentDisplayArea.querySelectorAll('.comment-group');
        let inserted = false;
        for (const group of existingGroups) {
          if (parseInt(group.dataset.blockIndex, 10) > blockIndex) {
            commentDisplayArea.insertBefore(blockCommentsContainer, group);
            inserted = true;
            break;
          }
        }
        if (!inserted) {
          commentDisplayArea.appendChild(blockCommentsContainer);
        }
      }
      const commentElement = createCommentElement(comment);
      commentElement.classList.add('comment-item');
      blockCommentsContainer.appendChild(commentElement);
    }

    function createCommentElement(comment) {
      // ... (createCommentElement remains the same) ...
      const div = document.createElement('div');
      div.classList.add(
          'comment-item', 'bg-gray-50', 'p-2', 'rounded', 'text-sm', 'mb-1',
          'border', 'border-gray-200', 'text-right', 'relative');
      div.dataset.commentId = comment.id;
      let deleteButtonHTML = '';
      if (CURRENT_USER_ID !== null && comment.author_id === CURRENT_USER_ID) {
        deleteButtonHTML =
            ` <button class="delete-comment-btn absolute top-1 left-1" data-comment-id="${
                comment.id}" title="حذف التعليق"> 🗑️ </button> `;
      }
      div.innerHTML = ` ${deleteButtonHTML} <p class="text-gray-800 mr-6">${
          comment
              .text}</p> <p class="text-xs text-gray-500 mt-1"> <span class="font-medium">${
          comment.author}</span> - ${comment.timestamp} </p> `;
      return div;
    }

    function clearCommentsDisplay() {
      // ... (clearCommentsDisplay remains the same) ...
      if (commentDisplayArea) {
        const groups = commentDisplayArea.querySelectorAll('.comment-group');
        groups.forEach(group => group.remove());
        if (noCommentsMsg) {
          noCommentsMsg.style.display = 'block';
        } else {
          const p = document.createElement('p');
          p.id = 'no-comments-msg';
          p.className = 'text-gray-500 text-sm';
          p.style.display = 'block';
          commentDisplayArea.appendChild(p);
        }
      }
    }

    function openCommentForm(blockIndex) {
      // ... (openCommentForm remains the same) ...
      currentEditingBlock = blockIndex;
      if (commentBlockIndexSpan)
        commentBlockIndexSpan.textContent = blockIndex + 1;
      commentText.value = '';
      commentStatus.textContent = '';
      commentFormContainer.classList.remove('hidden');
      commentText.focus();
      console.log(`Opened comment form for block index ${blockIndex}`);
    }

    function closeCommentForm() {
      // ... (closeCommentForm remains the same) ...
      commentFormContainer.classList.add('hidden');
      currentEditingBlock = null;
      commentText.value = '';
      commentStatus.textContent = '';
      console.log('Closed comment form.');
    }

    // --- REMOVED generatePdf function ---

  } else {
    console.log('Not on episode page, or required JS variables not defined.');
  }
});  // End DOMContentLoaded
