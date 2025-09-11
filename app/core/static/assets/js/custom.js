// Custom JS for success modal and pricing scroll
(function(){
  // Success Modal
  const modal=document.getElementById('reviewModal');
  if(modal){
    const closeBtn=modal.querySelector('#closeReviewModal');
    const hide=()=>{
      modal.classList.add('fadeOut');
      setTimeout(()=>{modal.style.display='none';},600);
    };
    // show modal (template renders display:none; we switch to flex)
    modal.style.display='flex';
    modal.classList.add('show');
    closeBtn&&closeBtn.addEventListener('click',hide);
    modal.addEventListener('click',e=>{if(e.target===modal) hide();});
    setTimeout(hide,2000);
  }

  // Pricing auto-scroll
  const row=document.querySelector('.pricing-two__tab-content-box .row');
  if(row){
    row.classList.add('scroll-row');
    let dir=1; // 1: right, -1: left
    let paused=false;
    const speed=0.6; // px per step (slower)

    /* ===== Manual Drag Scroll ===== */
    let isDown=false,startX,scrollLeft;
    const setPaused=(val)=>{paused=val;};

    row.addEventListener('mousedown',e=>{
      isDown=true;
      row.classList.add('dragging');
      startX=e.pageX-row.offsetLeft;
      scrollLeft=row.scrollLeft;
      setPaused(true);
    });
    row.addEventListener('mouseleave',()=>{
      if(!isDown) return;
      isDown=false;row.classList.remove('dragging');
      setPaused(false);
    });
    row.addEventListener('mouseup',()=>{
      if(!isDown) return;
      isDown=false;row.classList.remove('dragging');
      setPaused(false);
    });
    row.addEventListener('mousemove',e=>{
      if(!isDown) return;
      const x=e.pageX-row.offsetLeft;
      const walk=(x-startX)*1.2; // drag speed multiplier
      row.scrollLeft=scrollLeft-walk;
    });
    // touch support
    row.addEventListener('touchstart',e=>{
      setPaused(true);
      isDown=true;
      startX=e.touches[0].pageX-row.offsetLeft;
      scrollLeft=row.scrollLeft;
    },{passive:true});
    row.addEventListener('touchmove',e=>{
      if(!isDown) return;
      const x=e.touches[0].pageX-row.offsetLeft;
      const walk=(x-startX)*1.1;
      row.scrollLeft=scrollLeft-walk;
    },{passive:true});
    row.addEventListener('touchend',()=>{isDown=false; setPaused(false);});
    const step=()=>{
      if(paused) return;
      row.scrollBy({left:dir*speed,behavior:'smooth'});
      if(row.scrollLeft+row.clientWidth>=row.scrollWidth-2) dir=-1;
      if(row.scrollLeft<=2) dir=1;
    };
    const interval=setInterval(step,25); // slower frame rate
    // pause on hover / wheel / touch
    row.addEventListener('mouseenter',()=>paused=true);
    row.addEventListener('mouseleave',()=>paused=false);
    row.addEventListener('touchstart',()=>paused=true,{passive:true});
    row.addEventListener('wheel',()=>setPaused(true),{passive:true});
    row.addEventListener('touchend',()=>setPaused(false));
  }
})();
