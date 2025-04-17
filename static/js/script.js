// static/js/script.js (Arabic Version - Multi-Color Highlighting)

document.addEventListener('DOMContentLoaded', () => {
  console.log('DOM fully loaded and parsed - Main script.js running.');

  // --- Color Palette for Highlights ---
  const highlightColors = [
    'highlight-color-0',  // yellow-50
    'highlight-color-1',  // blue-50
    'highlight-color-2',  // green-50
    'highlight-color-3',  // red-50
    'highlight-color-4',  // violet-50
    'highlight-color-5',  // orange-50
  ];
  const numHighlightColors = highlightColors.length;

  // Helper function to get color class based on index
  const getColorClassForIndex = (index) => {
    if (index === null || index < 0) return '';  // No color if index is invalid
    return highlightColors[index % numHighlightColors];
  };
  // Helper function to remove all highlight classes from an element
  const removeHighlightClasses = (element) => {
    if (element) {
      highlightColors.forEach(cls => element.classList.remove(cls));
    }
  };

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

  let currentEditingBlock = null;

  // Check if we are on the episode page
  if (typeof EPISODE_ID !== 'undefined' && EPISODE_ID !== null &&
      typeof CURRENT_USER_ID !== 'undefined' &&
      typeof IS_ADMIN !== 'undefined') {
    console.log('Episode page detected. Initializing episode features.');
    console.log(`User ID: ${CURRENT_USER_ID}, Is Admin: ${IS_ADMIN}`);

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
    // ... (Save buttons, Toggle buttons remain the same) ...
    if (savePlanBtn && IS_ASSIGNED) {
      savePlanBtn.addEventListener('click', () => {
        saveContent('plan', planArea.value, planStatus).then(success => {
          if (success) renderPlanMarkdown(planArea.value);
        });
      });
    }
    if (saveScenarioBtn && IS_ASSIGNED) {
      saveScenarioBtn.addEventListener('click', () => {
        const newScenario = scenarioArea.value;
        saveContent('scenario', newScenario, scenarioStatus).then(success => {
          if (success) renderScenario(scenarioArea.value);
        });
      });
    }
    if (viewPlanBtn && editPlanBtn && planDisplay && planEditorWrapper &&
        IS_ASSIGNED) {
      viewPlanBtn.addEventListener('click', () => {
        planEditorWrapper.classList.add('hidden');
        planDisplay.classList.remove('hidden');
        renderPlanMarkdown(planArea.value);
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
        editPlanBtn.classList.add(
            'active', 'bg-indigo-100', 'text-indigo-700', 'font-medium');
        editPlanBtn.classList.remove('text-gray-600', 'hover:bg-gray-100');
        viewPlanBtn.classList.remove(
            'active', 'bg-indigo-100', 'text-indigo-700', 'font-medium');
        viewPlanBtn.classList.add('text-gray-600', 'hover:bg-gray-100');
        planArea.focus();
      });
    }
    if (viewScenarioBtnActual && editScenarioBtnActual && scenarioDisplay &&
        scenarioEditorWrapper && IS_ASSIGNED) {
      viewScenarioBtnActual.addEventListener('click', () => {
        scenarioEditorWrapper.classList.add('hidden');
        scenarioDisplay.classList.remove('hidden');
        if (commentInstruction) commentInstruction.style.display = 'block';
        renderScenario(scenarioArea.value);
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


    // --- Commenting Logic ---

    // Scenario Display Click (Add Comment)
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

    // Submit Comment Button
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
                addCommentToDisplay(
                    data.comment);  // This will handle highlighting
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

    // Cancel Comment Button
    if (cancelCommentBtn) {
      cancelCommentBtn.addEventListener('click', () => {
        closeCommentForm();
      });
    }

    // Comment Deletion (Event Delegation)
    if (commentDisplayArea) {
      commentDisplayArea.addEventListener('click', function(event) {
        const deleteButton = event.target.closest('.delete-comment-btn');
        if (deleteButton) {
          const commentElement = deleteButton.closest('.comment-item');
          const commentId = deleteButton.dataset.commentId;
          const commentGroup =
              commentElement ? commentElement.closest('.comment-group') : null;
          const blockIndex = commentGroup ?
              parseInt(commentGroup.dataset.blockIndex, 10) :
              null;  // Get block index

          if (commentId && commentElement && blockIndex !== null) {
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
                        // Check if the block group is now empty
                        if (commentGroup &&
                            !commentGroup.querySelector('.comment-item')) {
                          commentGroup.remove();  // Remove the group
                          // Remove highlight from the corresponding scenario
                          // block
                          const blockElement = scenarioDisplay.querySelector(
                              `.commentable-block[data-block-index="${
                                  blockIndex}"]`);
                          if (blockElement) {
                            removeHighlightClasses(
                                blockElement);  // Use helper to remove all
                                                // color classes
                          }
                        }
                        // Check if any comment groups left
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
      // ... (saveContent logic remains the same) ...
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

    /**
     * Renders the SCENARIO text as Markdown and makes blocks commentable.
     * Adds cycling highlight class to blocks with comments.
     * @param {string} scenarioText - The full scenario text.
     */
    function renderScenario(scenarioText) {
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
          // Remove any previous highlight first
          removeHighlightClasses(blockElement);
          // Add highlight class if comments exist for this block index
          if (typeof INITIAL_COMMENTS_BY_BLOCK !== 'undefined' &&
              INITIAL_COMMENTS_BY_BLOCK[i]) {
            const colorClass =
                getColorClassForIndex(i);  // Get color based on index
            if (colorClass) blockElement.classList.add(colorClass);
          }
        }
        if (!hasCommentableBlocks && scenarioText && scenarioText.trim()) {
          scenarioDisplay.innerHTML =
              `<div class="commentable-block" data-block-index="0">${
                  scenarioDisplay.innerHTML}</div>`;
          if (typeof INITIAL_COMMENTS_BY_BLOCK !== 'undefined' &&
              INITIAL_COMMENTS_BY_BLOCK[0]) {
            const colorClass = getColorClassForIndex(0);
            if (colorClass)
              scenarioDisplay.firstChild.classList.add(colorClass);
          }
        }
        console.log(
            `Rendered scenario as Markdown, added indices and highlights to ${
                children.length} blocks.`);
      } catch (e) {
        console.error('Error during scenario Markdown rendering:', e);
        scenarioDisplay.textContent = scenarioText;
      }
    }


    /**
     * Renders comments grouped by block index.
     * Adds cycling highlight class to comment groups.
     * @param {object} commentsByBlock - Object keyed by block_index.
     */
    function renderComments(commentsByBlock) {
      if (!commentDisplayArea) return;
      clearCommentsDisplay();

      let hasAnyComments = false;
      if (commentsByBlock && typeof commentsByBlock === 'object') {
        Object.keys(commentsByBlock)
            .sort((a, b) => parseInt(a, 10) - parseInt(b, 10))
            .forEach(blockIndexStr => {
              const blockIndex =
                  parseInt(blockIndexStr, 10);  // Ensure it's a number
              const comments = commentsByBlock[blockIndex];
              if (comments && comments.length > 0) {
                hasAnyComments = true;
                const blockCommentsContainer = document.createElement('div');
                const colorClass =
                    getColorClassForIndex(blockIndex);  // Get color class
                // Add highlight class to the comment group itself
                blockCommentsContainer.classList.add(
                    'comment-group', 'mb-3', 'border-r-4', 'pr-3',
                    'text-right');
                if (colorClass)
                  blockCommentsContainer.classList.add(
                      colorClass);  // Add the specific color class
                blockCommentsContainer.dataset.blockIndex = blockIndex;

                const blockHeader = document.createElement('h4');
                blockHeader.classList.add(
                    'text-sm', 'font-semibold', 'text-gray-600', 'mb-1');
                blockHeader.textContent =
                    `تعليقات للفقرة رقم ${blockIndex + 1}`;
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

    /**
     * Adds a single new comment to the display area, grouped by block index.
     * Ensures the group and scenario block are highlighted with the correct
     * color.
     * @param {object} comment - Comment object including block_index.
     */
    function addCommentToDisplay(comment) {
      if (!commentDisplayArea || comment.block_index === undefined) return;
      if (noCommentsMsg && noCommentsMsg.style.display !== 'none') {
        noCommentsMsg.style.display = 'none';
      }

      const blockIndex = comment.block_index;
      const colorClass = getColorClassForIndex(blockIndex);  // Get color class
      let blockCommentsContainer = commentDisplayArea.querySelector(
          `.comment-group[data-block-index="${blockIndex}"]`);

      // Ensure scenario block is highlighted with the correct color
      const blockElement = scenarioDisplay.querySelector(
          `.commentable-block[data-block-index="${blockIndex}"]`);
      if (blockElement) {
        removeHighlightClasses(blockElement);  // Remove old colors if any
        if (colorClass)
          blockElement.classList.add(colorClass);  // Add correct color
      }

      if (!blockCommentsContainer) {
        blockCommentsContainer = document.createElement('div');
        // Add highlight class when creating the group
        blockCommentsContainer.classList.add(
            'comment-group', 'mb-3', 'border-r-4', 'pr-3', 'text-right');
        if (colorClass)
          blockCommentsContainer.classList.add(
              colorClass);  // Add correct color
        blockCommentsContainer.dataset.blockIndex = blockIndex;

        const blockHeader = document.createElement('h4');
        blockHeader.classList.add(
            'text-sm', 'font-semibold', 'text-gray-600', 'mb-1');
        blockHeader.textContent = `تعليقات للفقرة رقم ${blockIndex + 1}`;
        blockCommentsContainer.appendChild(blockHeader);

        // Insert sorted
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
      } else {
        // Ensure existing group also has the correct highlight
        removeHighlightClasses(blockCommentsContainer);
        if (colorClass) blockCommentsContainer.classList.add(colorClass);
      }

      const commentElement = createCommentElement(comment);
      commentElement.classList.add('comment-item');
      blockCommentsContainer.appendChild(commentElement);
    }

    function createCommentElement(comment) {
      // ... (createCommentElement logic remains the same) ...
      const div = document.createElement('div');
      div.classList.add(
          'comment-item', 'bg-gray-50', 'p-2', 'rounded', 'text-sm', 'mb-1',
          'border', 'border-gray-200', 'text-right', 'relative');
      div.dataset.commentId = comment.id;
      let deleteButtonHTML = '';
      if (CURRENT_USER_ID !== null &&
          (comment.author_id === CURRENT_USER_ID || IS_ADMIN)) {
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

  } else {
    console.log('Not on episode page, or required JS variables not defined.');
  }
});  // End DOMContentLoaded
