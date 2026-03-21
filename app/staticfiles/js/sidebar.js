/**
 * CRM KIKI Sidebar Animations
 * Minimal, smooth interactions for sidebar
 */

document.addEventListener('DOMContentLoaded', function() {
    initSidebarAnimations();
});

function initSidebarAnimations() {
    const sidebar = document.querySelector('.crm-sidebar');
    if (!sidebar) return;

    const navLinks = sidebar.querySelectorAll('.nav-link:not(.disabled)');
    const navSections = sidebar.querySelectorAll('.nav-section');

    setupMobileSidebarToggle(sidebar);

    // Subtle entrance
    animateEntrance(navLinks, navSections);

    // Active indicator (visual only)
    setupActiveIndicator(sidebar);
}

function setupMobileSidebarToggle(sidebar) {
    const toggleBtn = document.getElementById('sidebarToggle');
    const overlay = document.getElementById('sidebarOverlay');

    const open = () => {
        sidebar.classList.add('active');
        if (overlay) overlay.classList.add('active');
        document.body.classList.add('sidebar-open');
    };

    const close = () => {
        sidebar.classList.remove('active');
        if (overlay) overlay.classList.remove('active');
        document.body.classList.remove('sidebar-open');
    };

    if (toggleBtn) {
        toggleBtn.addEventListener('click', function() {
            const isOpen = sidebar.classList.contains('active');
            if (isOpen) close();
            else open();
        });
    }

    if (overlay) {
        overlay.addEventListener('click', close);
    }

    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            close();
        }
    });

    // Close sidebar after navigating on mobile
    sidebar.querySelectorAll('.nav-link:not(.disabled)').forEach((link) => {
        link.addEventListener('click', function() {
            if (window.innerWidth <= 768) {
                close();
            }
        });
    });

    // Reset states when resizing from mobile to desktop
    window.addEventListener('resize', function() {
        if (window.innerWidth > 768) {
            close();
        }
    });
}

function animateEntrance(links, sections) {
    links.forEach((link, index) => {
        link.style.opacity = '0';
        setTimeout(() => {
            link.style.transition = 'opacity 0.25s ease';
            link.style.opacity = '1';
        }, 30 + (index * 25));
    });

    sections.forEach((section) => {
        section.style.opacity = '0';
        setTimeout(() => {
            section.style.transition = 'opacity 0.25s ease';
            section.style.opacity = '1';
        }, 50);
    });
}

function setupActiveIndicator(sidebar) {
    const indicator = document.createElement('div');
    indicator.className = 'sidebar-indicator';
    indicator.style.cssText = `
        position: absolute;
        left: 0;
        width: 3px;
        background: linear-gradient(180deg, #667eea 0%, #8b5cf6 100%);
        border-radius: 0 2px 2px 0;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        pointer-events: none;
        z-index: 10;
        opacity: 0;
    `;
    
    const nav = sidebar.querySelector('.sidebar-nav');
    if (nav) {
        nav.style.position = 'relative';
        nav.appendChild(indicator);
    }

    function updateIndicator() {
        const activeLink = sidebar.querySelector('.nav-link.active');
        if (activeLink && indicator) {
            const navRect = nav.getBoundingClientRect();
            const linkRect = activeLink.getBoundingClientRect();
            
            indicator.style.opacity = '1';
            indicator.style.top = `${linkRect.top - navRect.top}px`;
            indicator.style.height = `${linkRect.height}px`;
        }
    }

    updateIndicator();
    
    const observer = new MutationObserver(() => {
        requestAnimationFrame(updateIndicator);
    });
    
    sidebar.querySelectorAll('.nav-link').forEach(link => {
        observer.observe(link, { attributes: true, attributeFilter: ['class'] });
    });
}


