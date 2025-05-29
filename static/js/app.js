document.addEventListener("DOMContentLoaded", function () {
  // File input preview
  const fileInput = document.getElementById("image-upload");
  const fileLabel = document.querySelector(".file-label");
  const previewContainer = document.getElementById("preview-container");

  if (fileInput) {
    fileInput.addEventListener("change", function () {
      if (this.files && this.files[0]) {
        // Update label text with filename
        const fileName = this.files[0].name;
        if (fileLabel) {
          fileLabel.textContent =
            fileName.length > 20 ? fileName.substring(0, 20) + "..." : fileName;
        }

        // Show image preview if we're on the upload page
        if (previewContainer) {
          previewContainer.innerHTML = "";
          const reader = new FileReader();

          reader.onload = function (e) {
            const img = document.createElement("img");
            img.src = e.target.result;
            img.className = "preview-image";
            previewContainer.appendChild(img);
          };

          reader.readAsDataURL(this.files[0]);
        }

        // Auto-submit the form if it has data-auto-submit attribute
        const form = this.closest("form[data-auto-submit]");
        if (form) {
          form.submit();
        }
      }
    });
  }

  // Filter selection
  const filterOptions = document.querySelectorAll(".filter-option");
  const filterInput = document.getElementById("selected-filter");

  if (filterOptions.length && filterInput) {
    filterOptions.forEach((option) => {
      option.addEventListener("click", function () {
        // Remove active class from all options
        filterOptions.forEach((opt) => opt.classList.remove("active"));

        // Add active class to selected option
        this.classList.add("active");

        // Update hidden input value
        filterInput.value = this.dataset.filter;
      });
    });
  }

  // Form submission loading indicator
  const forms = document.querySelectorAll("form");
  forms.forEach((form) => {
    form.addEventListener("submit", function () {
      const loadingEl = this.querySelector(".loading");
      const submitBtn = this.querySelector('button[type="submit"]');

      if (loadingEl) {
        loadingEl.style.display = "flex";
      }

      if (submitBtn) {
        submitBtn.disabled = true;
      }
    });
  });
});
