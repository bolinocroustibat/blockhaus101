document.addEventListener('DOMContentLoaded', () => {
    // Image loading animation
    const images = document.querySelectorAll('.expo-wrapper img');
    images.forEach(img => {
        if (img.complete) {
            // Image is already loaded (from cache)
            img.classList.add('loaded');
        } else {
            // Wait for image to load
            img.addEventListener('load', () => {
                img.classList.add('loaded');
            });
        }
    });
});
