<script>
  import Icon from "@iconify/svelte";

  let show = false;
  setTimeout(() => (show = true), 300);
</script>

{#if show}
  <div class="outer">
    <div class="inner">
      <Icon icon="game-icons:knife-fork" width="150" />
    </div>
  </div>
{/if}

<style>
  div.outer {
    display: inline-block;
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translateY(-50%) translateX(-50%);
  }

  div.inner {
    animation-name: spin;
    animation-duration: 1000ms;
    animation-iteration-count: infinite;
    animation-timing-function: linear;
    opacity: 0.8;
  }

  @keyframes spin {
    from {
      transform: rotate(0deg);
    }
    to {
      transform: rotate(360deg);
    }
  }
</style>
